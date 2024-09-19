import eth_abi
from eth_utils import keccak
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.constants import NEON_CORE_API_URL
from integration.tests.neon_evm.utils.contract import deploy_contract, make_contract_call_trx
from integration.tests.neon_evm.utils.ethereum import make_eth_transaction
from integration.tests.neon_evm.utils.neon_api_client import NeonApiClient
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text
from utils.consts import SOLANA_CALL_PRECOMPILED_ID
from utils.helpers import bytes32_to_solana_pubkey, serialize_instruction
from utils.metaplex import SYSTEM_PROGRAM_ID


class SolanaCaller:
    def __init__(self, operator_keypair, owner, evm_loader, treasury_pool, holder_acc):
        self.operator_keypair = operator_keypair
        self.owner = owner
        self.evm_loader = evm_loader
        self.treasury_pool = treasury_pool
        self.holder_acc = holder_acc
        self.neon_api_client = NeonApiClient(url=NEON_CORE_API_URL)

        self.contract = deploy_contract(
            operator_keypair, owner, "precompiled/CallSolanaCaller", evm_loader, treasury_pool, version="0.8.10"
        )

    def get_neon_address(self, eth_address):
        args = eth_abi.encode(["address"], [eth_address])
        addr = self.neon_api_client.call_contract_get_function(
            self.owner, self.contract, "getNeonAddress(address)", args
        )
        return addr

    def get_payer(self):
        payer_bytes32 = self.neon_api_client.call_contract_get_function(self.owner, self.contract, "getPayer()")
        return bytes32_to_solana_pubkey(payer_bytes32)

    def get_solana_address_by_neon_address(self, neon_address):
        args = eth_abi.encode(["address"], [neon_address])
        sol_addr = self.neon_api_client.call_contract_get_function(
            self.owner, self.contract, "getNeonAddress(address)", args
        )
        return bytes32_to_solana_pubkey(sol_addr)

    def get_solana_PDA(self, program_id, seeds) -> Pubkey:
        args = eth_abi.encode(["bytes32", "bytes"], [bytes(program_id), seeds])
        addr = self.neon_api_client.call_contract_get_function(
            self.owner, self.contract, "getSolanaPDA(bytes32,bytes)", args
        )
        return bytes32_to_solana_pubkey(addr)

    def get_eth_ext_authority(self, salt, sender) -> Pubkey:
        args = eth_abi.encode(["bytes32"], [salt])
        addr = self.neon_api_client.call_contract_get_function(
            sender, self.contract, "getExtAuthority(bytes32)", args
        )
        return bytes32_to_solana_pubkey(addr)

    def execute(self, program_id, instruction, lamports=0, holder_acc=None, sender=None, additional_accounts=None):
        sender = self.owner if sender is None else sender
        holder_acc = self.holder_acc if holder_acc is None else holder_acc
        serialized_instructions = serialize_instruction(program_id, instruction)
        signed_tx = make_contract_call_trx(self.evm_loader,
            sender, self.contract, "execute(uint64,bytes)", [lamports, serialized_instructions]
        )
        resp = self.evm_loader.execute_trx_from_instruction_with_solana_call(
            self.operator_keypair,
            holder_acc,
            self.treasury_pool.account,
            self.treasury_pool.buffer,
            signed_tx,
            [
                sender.balance_account_address,
                sender.solana_account_address,
                SOLANA_CALL_PRECOMPILED_ID,
                self.contract.balance_account_address,
                self.contract.solana_address,
                program_id,
            ]
            + (additional_accounts or [])
            + self._get_all_pubkeys_from_instructions([instruction]),
        )
        return resp

    def execute_with_seed(self, program_id, instruction, seed, lamports=0, holder_acc=None, sender=None, additional_accounts=None):
        sender = self.owner if sender is None else sender
        holder_acc = self.holder_acc if holder_acc is None else holder_acc
        serialized_instructions = serialize_instruction(program_id, instruction)
        signed_tx = make_contract_call_trx(self.evm_loader,
            sender, self.contract, "executeWithSeed(uint64,bytes32,bytes)", [lamports, seed, serialized_instructions]
        )
        resp = self.evm_loader.execute_trx_from_instruction_with_solana_call(
            self.operator_keypair,
            holder_acc,
            self.treasury_pool.account,
            self.treasury_pool.buffer,
            signed_tx,
            [
                sender.balance_account_address,
                sender.solana_account_address,
                SOLANA_CALL_PRECOMPILED_ID,
                self.contract.balance_account_address,
                self.contract.solana_address,
                program_id,
            ]
            + (additional_accounts or []) +
            self._get_all_pubkeys_from_instructions([instruction]))
        return resp

    def batch_execute(self, call_params, sender=None, additional_accounts=None, additional_signers=None):
        # call_params = [(program_id, lamports, instruction), ...]
        execute_params = []
        for program_id, lamports, instruction in call_params:
            serialized_instruction = serialize_instruction(program_id, instruction)
            execute_params.append((lamports, serialized_instruction))
        calldata = keccak(text="batchExecute((uint64,bytes)[])")[:4] + eth_abi.encode(
            ["(uint64,bytes)[]"],
            [execute_params],
        )

        signed_tx = make_eth_transaction(self.evm_loader, self.contract.eth_address, calldata, sender)

        self.evm_loader.write_transaction_to_holder_account(signed_tx, self.holder_acc, self.operator_keypair)
        accounts = (
            [
                sender.balance_account_address,
                sender.solana_account_address,
                self.contract.balance_account_address,
                self.contract.solana_address,
                SOLANA_CALL_PRECOMPILED_ID,
            ]
            + [item[0] for item in call_params]
            + self._get_all_pubkeys_from_instructions([item[2] for item in call_params])
            + (additional_accounts or [])
        )

        resp = self.evm_loader.execute_trx_from_account_with_solana_call(
            self.operator_keypair,
            self.holder_acc,
            self.treasury_pool.account,
            self.treasury_pool.buffer,
            accounts,
            self.operator_keypair, additional_signers,
        )
        return resp

    def get_resource_address(self, salt, sender):
        encoded_args = eth_abi.encode(["bytes32"], [salt])

        resource_address = self.neon_api_client.call_contract_get_function(
            sender, self.contract, "getResourceAddress(bytes32)", encoded_args
        )
        return bytes32_to_solana_pubkey(resource_address)

    def create_resource(self, sender, salt, space, lamports, owner):
        signed_tx = make_contract_call_trx(self.evm_loader,
            sender, self.contract, "createResource(bytes32,uint64,uint64,bytes32)", [salt, space, lamports, bytes(owner)]
        )
        self.evm_loader.write_transaction_to_holder_account(signed_tx, self.holder_acc, self.operator_keypair)
        resource_address_pubkey = self.get_resource_address(salt, sender)

        resp = self.evm_loader.execute_trx_from_account_with_solana_call(
            self.operator_keypair,
            self.holder_acc,
            self.treasury_pool.account,
            self.treasury_pool.buffer,
            [
                self.contract.balance_account_address,
                self.contract.solana_address,
                sender.balance_account_address,
                sender.solana_account_address,
                SOLANA_CALL_PRECOMPILED_ID,
                resource_address_pubkey,
                SYSTEM_PROGRAM_ID

            ]        )
        check_transaction_logs_have_text(resp, "exit_status=0x12")
        return resource_address_pubkey

    @staticmethod
    def _get_all_pubkeys_from_instructions(instructions):
        all_keys = []
        for item in instructions:
            all_keys += item.accounts
        return [acc.pubkey for acc in all_keys]
