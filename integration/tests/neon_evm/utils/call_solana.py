import eth_abi
from eth_utils import keccak
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.ethereum import make_eth_transaction, make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text
from utils.consts import SOLANA_CALL_PRECOMPILED_ID
from utils.evm_loader import EvmLoader
from utils.helpers import bytes32_to_solana_pubkey, serialize_instruction, serialize_instruction_struct
from utils.metaplex import SYSTEM_PROGRAM_ID


class SolanaCaller:
    def __init__(
        self,
        operator_keypair,
        owner,
        evm_loader: EvmLoader,
        treasury_pool,
        holder_acc,
        neon_rpc_client,
    ) -> None:
        self.operator_keypair = operator_keypair
        self.owner = owner
        self.evm_loader = evm_loader
        self.treasury_pool = treasury_pool
        self.holder_acc = holder_acc
        self.neon_rpc_client = neon_rpc_client
        self.contract = evm_loader.deploy_contract(
            operator=operator_keypair,
            user=owner,
            contract_file_name="precompiled/CallSolanaCaller",
            neon_rpc_client=neon_rpc_client,
            treasury_pool=treasury_pool,
            contract_name="CallSolanaCaller",
            version="0.8.28",
        )

    def get_neon_address(self, eth_address):
        args = eth_abi.encode(["address"], [eth_address])
        addr = self.neon_rpc_client.call_contract_get_function(
            self.owner, self.contract, "getNeonAddress(address)", args
        )
        return addr

    def get_payer(self):
        payer_bytes32 = self.neon_rpc_client.call_contract_get_function(self.owner, self.contract, "getPayer()")
        return bytes32_to_solana_pubkey(payer_bytes32)

    def get_solana_address_by_neon_address(self, neon_address):
        args = eth_abi.encode(["address"], [neon_address])
        sol_addr = self.neon_rpc_client.call_contract_get_function(
            self.owner, self.contract, "getNeonAddress(address)", args
        )
        return bytes32_to_solana_pubkey(sol_addr)

    def get_solana_PDA(self, program_id, seeds) -> Pubkey:
        args = eth_abi.encode(["bytes32", "bytes"], [bytes(program_id), seeds])
        addr = self.neon_rpc_client.call_contract_get_function(
            self.owner, self.contract, "getSolanaPDA(bytes32,bytes)", args
        )
        return bytes32_to_solana_pubkey(addr)

    def get_eth_ext_authority(self, salt, sender) -> Pubkey:
        args = eth_abi.encode(["bytes32"], [salt])
        addr = self.neon_rpc_client.call_contract_get_function(sender, self.contract, "getExtAuthority(bytes32)", args)
        return bytes32_to_solana_pubkey(addr)

    def execute(self, program_id, instruction, lamports=None, holder_acc=None, sender=None):
        sender = self.owner if sender is None else sender
        holder_acc = self.holder_acc if holder_acc is None else holder_acc
        serialized_instructions = serialize_instruction(program_id, instruction)

        if lamports is not None:
            signed_tx = make_contract_call_trx(
                self.evm_loader, sender, self.contract, "execute(uint64,bytes)", [lamports, serialized_instructions]
            )
        else:
            signed_tx = make_contract_call_trx(
                self.evm_loader, sender, self.contract, "execute(bytes)", [serialized_instructions]
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
            + self._get_all_pubkeys_from_instructions([instruction]),
        )
        return resp

    def execute_with_seed(
        self,
        program_id,
        instruction,
        seed,
        lamports=None,
        holder_acc=None,
        sender=None,
    ):
        sender = self.owner if sender is None else sender
        holder_acc = self.holder_acc if holder_acc is None else holder_acc
        serialized_instructions = serialize_instruction(program_id, instruction)
        if lamports is not None:
            signed_tx = make_contract_call_trx(
                self.evm_loader,
                sender,
                self.contract,
                "executeWithSeed(uint64,bytes32,bytes)",
                [lamports, seed, serialized_instructions],
            )
        else:
            signed_tx = make_contract_call_trx(
                self.evm_loader,
                sender,
                self.contract,
                "executeWithSeed(bytes32,bytes)",
                [seed, serialized_instructions],
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
            + self._get_all_pubkeys_from_instructions([instruction]),
        )
        return resp

    def batch_execute(
        self, call_params, sender=None, additional_signers=None, is_iterative=False, skip_preflight=False
    ):
        # call_params = [(program_id, lamports, instruction), ...]
        if len(call_params[0]) == 2:  # check lamport
            method_signature = "batchExecuteWithoutLamports(bytes[])"
            abi_type = ["bytes[]"]

            execute_params = [serialize_instruction(program_id, instruction) for program_id, instruction in call_params]
        else:
            method_signature = "batchExecute((uint64,bytes)[])"
            abi_type = ["(uint64,bytes)[]"]
            execute_params = [
                (lamports, serialize_instruction(program_id, instruction))
                for program_id, lamports, instruction in call_params
            ]

        calldata = keccak(text=method_signature)[:4] + eth_abi.encode(abi_type, [execute_params])
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
            + self._get_all_pubkeys_from_instructions([item[-1] for item in call_params])
        )
        if is_iterative:
            resp = self.evm_loader.execute_transaction_steps_from_account(
                self.operator_keypair,
                self.treasury_pool,
                self.holder_acc,
                accounts,
                self.operator_keypair,
                additional_signers=additional_signers,
            )
        else:
            resp = self.evm_loader.execute_trx_from_account_with_solana_call(
                self.operator_keypair,
                self.holder_acc,
                self.treasury_pool.account,
                self.treasury_pool.buffer,
                accounts,
                self.operator_keypair,
                additional_signers=additional_signers,
                skip_preflight=skip_preflight,
            )
        return resp

    def execute_with_instruction_struct(self, instruction, lamports=None, holder_acc=None, sender=None):
        sender = sender or self.owner
        holder_acc = holder_acc or self.holder_acc
        serialized_prog_id, serialized_accounts, serialized_data = serialize_instruction_struct(instruction)
        if lamports is not None:
            function_signature = "execute(uint64,(bytes32,(bytes32,bool,bool)[],bytes))"
            params = [lamports, (serialized_prog_id, serialized_accounts, serialized_data)]
        else:
            function_signature = "execute((bytes32,(bytes32,bool,bool)[],bytes))"
            params = [(serialized_prog_id, serialized_accounts, serialized_data)]

        signed_tx = make_contract_call_trx(
            evm_loader=self.evm_loader,
            user=sender,
            contract=self.contract,
            function_signature=function_signature,
            params=params,
        )

        accounts = [
            sender.balance_account_address,
            sender.solana_account_address,
            SOLANA_CALL_PRECOMPILED_ID,
            self.contract.balance_account_address,
            self.contract.solana_address,
            instruction.program_id,
        ] + [acc.pubkey for acc in instruction.accounts]

        return self.evm_loader.execute_trx_from_instruction_with_solana_call(
            self.operator_keypair,
            holder_acc,
            self.treasury_pool.account,
            self.treasury_pool.buffer,
            signed_tx,
            accounts,
        )

    def execute_with_seed_and_instruction_struct(
        self,
        seed,
        instruction,
        lamports=None,
        holder_acc=None,
        sender=None,
        additional_signers=None,
    ):
        sender = sender or self.owner
        holder_acc = holder_acc or self.holder_acc

        serialized_prog_id, serialized_accounts, serialized_data = serialize_instruction_struct(instruction)

        if lamports is not None:
            function_signature = "executeWithSeed(uint64,bytes32,(bytes32,(bytes32,bool,bool)[],bytes))"
            params = [lamports, seed, (serialized_prog_id, serialized_accounts, serialized_data)]
        else:
            function_signature = "executeWithSeed(bytes32,(bytes32,(bytes32,bool,bool)[],bytes))"
            params = [seed, (serialized_prog_id, serialized_accounts, serialized_data)]

        signed_tx = make_contract_call_trx(
            evm_loader=self.evm_loader,
            user=sender,
            contract=self.contract,
            function_signature=function_signature,
            params=params,
        )

        self.evm_loader.write_transaction_to_holder_account(signed_tx, self.holder_acc, self.operator_keypair)
        accounts = [
            sender.balance_account_address,
            sender.solana_account_address,
            SOLANA_CALL_PRECOMPILED_ID,
            self.contract.balance_account_address,
            self.contract.solana_address,
            instruction.program_id,
        ] + [acc.pubkey for acc in instruction.accounts]

        return self.evm_loader.execute_transaction_steps_from_account(
            self.operator_keypair,
            self.treasury_pool,
            self.holder_acc,
            accounts,
            self.operator_keypair,
            additional_signers=additional_signers,
        )

    def get_resource_address(self, salt, sender):
        encoded_args = eth_abi.encode(["bytes32"], [salt])

        resource_address = self.neon_rpc_client.call_contract_get_function(
            sender, self.contract, "getResourceAddress(bytes32)", encoded_args
        )
        return bytes32_to_solana_pubkey(resource_address)

    def create_resource(self, sender, salt, space, lamports, owner):
        resource_address_pubkey = self.get_resource_address(salt, sender)
        if self.evm_loader.account_exists(resource_address_pubkey):
            return resource_address_pubkey

        signed_tx = make_contract_call_trx(
            self.evm_loader,
            sender,
            self.contract,
            "createResource(bytes32,uint64,uint64,bytes32)",
            [salt, space, lamports, bytes(owner)],
        )
        self.evm_loader.write_transaction_to_holder_account(signed_tx, self.holder_acc, self.operator_keypair)

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
                SYSTEM_PROGRAM_ID,
            ],
        )
        check_transaction_logs_have_text(solana_client=self.evm_loader, trx=resp, text="exit_status=0x12")
        return resource_address_pubkey

    @staticmethod
    def _get_all_pubkeys_from_instructions(instructions):
        all_keys = []
        for item in instructions:
            all_keys += item.accounts
        return [acc.pubkey for acc in all_keys]
