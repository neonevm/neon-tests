import json
import typing
from typing import Union

import spl
import typing as tp

from eth_keys import keys as eth_keys
from eth_account.datastructures import SignedTransaction
from solana.keypair import Keypair
from solana.publickey import PublicKey
import solana.system_program as sp
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.rpc.responses import SendTransactionResp, GetTransactionResp
from spl.token.instructions import get_associated_token_address, MintToParams, ApproveParams, approve
from spl.token.constants import TOKEN_PROGRAM_ID

from integration.tests.neon_evm.utils.constants import (
    TREASURY_POOL_SEED,
    NEON_TOKEN_MINT_ID,
    CHAIN_ID,
)
from utils.consts import LAMPORT_PER_SOL, wSOL
from utils.instructions import (
    TransactionWithComputeBudget,
    make_ExecuteTrxFromInstruction,
    make_WriteHolder,
    make_ExecuteTrxFromAccount,
    make_PartialCallOrContinueFromRawEthereumTX,
    make_ExecuteTrxFromAccountDataIterativeOrContinue,
    make_CreateBalanceAccount,
    make_CreateAssociatedTokenIdempotent,
    make_DepositV03,
    make_wSOL,
    make_OperatorBalanceAccount,
)
from utils.layouts import BALANCE_ACCOUNT_LAYOUT, CONTRACT_ACCOUNT_LAYOUT, STORAGE_CELL_LAYOUT
from utils.solana_client import SolanaClient
from utils.types import Caller

EVM_STEPS = 500


class EvmLoader(SolanaClient):
    def __init__(self, program_id, endpoint):
        super().__init__(endpoint)
        EvmLoader.loader_id = PublicKey(program_id)
        self.loader_id = EvmLoader.loader_id

    def create_balance_account(self, ether: Union[str, bytes], sender, chain_id=CHAIN_ID) -> PublicKey:
        account_pubkey = self.ether2balance(ether, chain_id)
        contract_pubkey = PublicKey(self.ether2program(ether)[0])
        trx = Transaction()
        trx.add(
            make_CreateBalanceAccount(
                self.loader_id, sender.public_key, self.ether2bytes(ether), account_pubkey, contract_pubkey, chain_id
            )
        )
        self.send_tx(trx, sender)
        return account_pubkey

    def create_treasury_pool_address(self, pool_index):
        return PublicKey.find_program_address(
            [bytes(TREASURY_POOL_SEED, "utf8"), pool_index.to_bytes(4, "little")], self.loader_id
        )[0]

    @staticmethod
    def ether2bytes(ether: Union[str, bytes]):
        if isinstance(ether, str):
            if ether.startswith("0x"):
                return bytes.fromhex(ether[2:])
            return bytes.fromhex(ether)
        return ether

    @staticmethod
    def ether2hex(ether: Union[str, bytes]):
        if isinstance(ether, str):
            if ether.startswith("0x"):
                return ether[2:]
            return ether
        return ether.hex()

    def ether2operator_balance(
        self, keypair: Keypair, ether_address: Union[str, bytes], chain_id=CHAIN_ID
    ) -> PublicKey:
        address_bytes = self.ether2bytes(ether_address)
        key = bytes(keypair.public_key)
        chain_id_bytes = chain_id.to_bytes(32, "big")
        return PublicKey.find_program_address(
            [self.account_seed_version, key, address_bytes, chain_id_bytes], self.loader_id
        )[0]

    def get_neon_nonce(self, account: Union[str, bytes], chain_id=CHAIN_ID) -> int:
        solana_address = self.ether2balance(account, chain_id)

        info: bytes = self.get_solana_account_data(solana_address, BALANCE_ACCOUNT_LAYOUT.sizeof())
        layout = BALANCE_ACCOUNT_LAYOUT.parse(info)

        return layout.trx_count

    def get_solana_account_data(self, account: Union[str, PublicKey, Keypair], expected_length: int) -> bytes:
        if isinstance(account, Keypair):
            account = account.public_key
        info = self.get_account_info(account, commitment=Confirmed)
        info = info.value
        if info is None:
            raise Exception("Can't get information about {}".format(account))
        if len(info.data) < expected_length:
            print("len(data)({}) < expected_length({})".format(len(info.data), expected_length))
            raise Exception("Wrong data length for account data {}".format(account))
        return info.data

    def get_neon_balance(self, account: Union[str, bytes], chain_id=CHAIN_ID) -> int:
        balance_address = self.ether2balance(account, chain_id)

        info: bytes = self.get_solana_account_data(balance_address, BALANCE_ACCOUNT_LAYOUT.sizeof())
        layout = BALANCE_ACCOUNT_LAYOUT.parse(info)

        return int.from_bytes(layout.balance, byteorder="little")

    def get_contract_account_revision(self, address):
        account_data = self.get_solana_account_data(address, CONTRACT_ACCOUNT_LAYOUT.sizeof())
        return CONTRACT_ACCOUNT_LAYOUT.parse(account_data).revision

    def get_data_account_revision(self, address):
        account_data = self.get_solana_account_data(address, STORAGE_CELL_LAYOUT.sizeof())
        return STORAGE_CELL_LAYOUT.parse(account_data).revision

    def write_transaction_to_holder_account(
        self,
        signed_tx: SignedTransaction,
        holder_account: PublicKey,
        operator: Keypair,
    ):
        offset = 0
        receipts = []
        rest = signed_tx.rawTransaction
        while len(rest):
            (part, rest) = (rest[:920], rest[920:])
            trx = Transaction()
            trx.add(make_WriteHolder(operator.public_key, self.loader_id, holder_account, signed_tx.hash, offset, part))
            receipts.append(
                self.send_transaction(
                    trx,
                    operator,
                    opts=TxOpts(skip_confirmation=True, preflight_commitment=Confirmed),
                )
            )
            offset += len(part)

        for rcpt in receipts:
            self.confirm_transaction(rcpt.value, commitment=Confirmed)

    def ether2program(self, ether: tp.Union[str, bytes]) -> tp.Tuple[str, int]:
        items = PublicKey.find_program_address([self.account_seed_version, self.ether2bytes(ether)], self.loader_id)
        return str(items[0]), items[1]

    def ether2balance(self, address: tp.Union[str, bytes], chain_id=CHAIN_ID) -> PublicKey:
        # get public key associated with chain_id for an address
        address_bytes = self.ether2bytes(address)

        chain_id_bytes = chain_id.to_bytes(32, "big")
        return PublicKey.find_program_address(
            [self.account_seed_version, address_bytes, chain_id_bytes], self.loader_id
        )[0]

    def get_operator_balance_pubkey(self, operator: Keypair):
        operator_ether = eth_keys.PrivateKey(operator.secret_key[:32]).public_key.to_canonical_address()
        return self.ether2operator_balance(operator, operator_ether)

    def execute_trx_from_instruction(
        self,
        operator: Keypair,
        holder_acc: PublicKey,
        treasury_address: PublicKey,
        treasury_buffer: bytes,
        instruction: SignedTransaction,
        additional_accounts,
        signer: Keypair = None,
        system_program=sp.SYS_PROGRAM_ID,
        compute_unit_price=None
    ) -> SendTransactionResp:
        signer = operator if signer is None else signer
        trx = TransactionWithComputeBudget(operator, compute_unit_price=compute_unit_price)
        operator_balance = self.get_operator_balance_pubkey(operator)

        trx.add(
            make_ExecuteTrxFromInstruction(
                operator,
                operator_balance,
                holder_acc,
                self.loader_id,
                treasury_address,
                treasury_buffer,
                instruction.rawTransaction,
                additional_accounts,
                system_program)
        )

        return self.send_tx(trx, signer)

    def execute_trx_from_account(
        self,
        operator: Keypair,
        holder_acc: PublicKey,
        treasury_address: PublicKey,
        treasury_buffer: bytes,
        additional_accounts,
        signer: Keypair,
        system_program=sp.SYS_PROGRAM_ID,
    ) -> SendTransactionResp:
        operator_balance = self.get_operator_balance_pubkey(operator)

        trx = TransactionWithComputeBudget(operator)
        trx.add(
            make_ExecuteTrxFromAccount(
                operator,
                operator_balance,
                self.loader_id,
                holder_acc,
                treasury_address,
                treasury_buffer,
                additional_accounts,
                system_program=system_program,
            )
        )

        return self.send_tx(trx, signer)

    def execute_trx_from_instruction_with_solana_call(
        self,
        operator: Keypair,
        holder_address: PublicKey,
        treasury_address: PublicKey,
        treasury_buffer: bytes,
        instruction: SignedTransaction,
        additional_accounts,
        signer: Keypair = None,
        system_program=sp.SYS_PROGRAM_ID,
    ) -> SendTransactionResp:
        signer = operator if signer is None else signer
        operator_balance_pubkey = self.get_operator_balance_pubkey(operator)
        trx = TransactionWithComputeBudget(operator)
        trx.add(
            make_ExecuteTrxFromInstruction(
                operator,
                operator_balance_pubkey,
                holder_address,
                self.loader_id,
                treasury_address,
                treasury_buffer,
                instruction.rawTransaction,
                additional_accounts,
                system_program,
                tag=0x3E,
            )
        )
        return self.send_tx(trx, signer)

    def execute_trx_from_account_with_solana_call(
        self,
        operator: Keypair,
        holder_address,
        treasury_address: PublicKey,
        treasury_buffer: bytes,
        additional_accounts,
        signer: Keypair = None,
        additional_signers: typing.List[Keypair] = None,
        system_program=sp.SYS_PROGRAM_ID,
    ) -> SendTransactionResp:
        signer = operator if signer is None else signer
        operator_balance_pubkey = self.get_operator_balance_pubkey(operator)
        trx = TransactionWithComputeBudget(operator)
        trx.add(
            make_ExecuteTrxFromAccount(
                operator,
                operator_balance_pubkey,
                self.loader_id,
                holder_address,
                treasury_address,
                treasury_buffer,
                additional_accounts,
                additional_signers,
                system_program,
                tag=0x39,
            )
        )

        signers = [signer, *additional_signers] if additional_signers else [signer]
        return self.send_tx(trx, *signers)

    def send_transaction_step_from_instruction(
        self,
        operator: Keypair,
        operator_balance_pubkey,
        treasury,
        storage_account,
        instruction: SignedTransaction,
        additional_accounts,
        steps_count,
        signer: Keypair,
        system_program=sp.SYS_PROGRAM_ID,
        index=0,
        tag=0x34,
    ) -> GetTransactionResp:
        trx = TransactionWithComputeBudget(operator)

        trx.add(
            make_PartialCallOrContinueFromRawEthereumTX(
                index,
                steps_count,
                instruction.rawTransaction,
                operator,
                operator_balance_pubkey,
                self.loader_id,
                storage_account,
                treasury,
                additional_accounts,
                system_program,
                tag
            )
        )

        return self.send_tx(trx, signer)

    def execute_transaction_steps_from_instruction(
        self,
        operator: Keypair,
        treasury,
        storage_account,
        instruction: SignedTransaction,
        additional_accounts,
        signer: Keypair = None,
    ) -> GetTransactionResp:
        signer = operator if signer is None else signer
        operator_balance_pubkey = self.get_operator_balance_pubkey(operator)
        index = 0
        receipt = None
        done = False
        while not done:
            receipt = self.send_transaction_step_from_instruction(
                operator,
                operator_balance_pubkey,
                treasury,
                storage_account,
                instruction,
                additional_accounts,
                EVM_STEPS,
                signer,
                index=index,
            )
            index += 1

            if receipt.value.transaction.meta.err:
                raise AssertionError(f"Transaction failed with error: {receipt.value.transaction.meta.err}")
            for log in receipt.value.transaction.meta.log_messages:
                if "exit_status" in log:
                    done = True
                    break
                if "ExitError" in log:
                    raise AssertionError(f"EVM Return error in logs: {receipt}")

        return receipt

    def send_transaction_step_from_account(
        self,
        operator: Keypair,
        operator_balance_pubkey,
        treasury,
        storage_account,
        additional_accounts,
        steps_count,
        signer: Keypair,
        system_program=sp.SYS_PROGRAM_ID,
        compute_unit_price = None,
        tag=0x35,
        index=0,
    ) -> GetTransactionResp:
        trx = TransactionWithComputeBudget(operator, compute_unit_price=compute_unit_price)
        trx.add(
            make_ExecuteTrxFromAccountDataIterativeOrContinue(
                index,
                steps_count,
                operator,
                operator_balance_pubkey,
                self.loader_id,
                storage_account,
                treasury,
                additional_accounts,
                system_program,
                tag
            )
        )
        return self.send_tx(trx, signer)

    def execute_transaction_steps_from_account(
        self,
        operator: Keypair,
        treasury,
        storage_account,
        additional_accounts,
        signer: Keypair = None,
        compute_unit_price = None
    ) -> GetTransactionResp:
        signer = operator if signer is None else signer
        operator_balance_pubkey = self.get_operator_balance_pubkey(operator)

        index = 0
        receipt = None
        done = False
        while not done:
            receipt = self.send_transaction_step_from_account(
                operator,
                operator_balance_pubkey,
                treasury,
                storage_account,
                additional_accounts,
                EVM_STEPS,
                signer,
                index=index,
                compute_unit_price=compute_unit_price
            )
            index += 1

            if receipt.value.transaction.meta.err:
                raise AssertionError(f"Can't deploy contract: {receipt.value.transaction.meta.err}")
            for log in receipt.value.transaction.meta.log_messages:
                if "exit_status" in log:
                    done = True
                    break
                if "ExitError" in log:
                    raise AssertionError(f"EVM Return error in logs: {receipt}")

        return receipt

    def execute_transaction_steps_from_account_no_chain_id(
        self, operator: Keypair, treasury, storage_account, additional_accounts, signer: Keypair = None
    ) -> GetTransactionResp:
        signer = operator if signer is None else signer
        operator_balance_pubkey = self.get_operator_balance_pubkey(operator)
        index = 0
        receipt = None
        done = False
        while not done:
            receipt = self.send_transaction_step_from_account(
                operator,
                operator_balance_pubkey,
                treasury,
                storage_account,
                additional_accounts,
                EVM_STEPS,
                signer,
                tag=0x36,
                index=index
            )
            index += 1


            if receipt.value.transaction.meta.err:
                raise AssertionError(f"Can't deploy contract: {receipt.value.transaction.meta.err}")
            for log in receipt.value.transaction.meta.log_messages:
                if "exit_status" in log:
                    done = True
                    break
                if "ExitError" in log:
                    raise AssertionError(f"EVM Return error in logs: {receipt}")

        return receipt

    def deposit_neon(self, operator_keypair: Keypair, ether_address: Union[str, bytes], amount: int):
        balance_pubkey = self.ether2balance(ether_address)
        contract_pubkey = PublicKey(self.ether2program(ether_address)[0])

        evm_token_authority = PublicKey.find_program_address([b"Deposit"], self.loader_id)[0]
        evm_pool_key = get_associated_token_address(evm_token_authority, NEON_TOKEN_MINT_ID)

        token_pubkey = get_associated_token_address(operator_keypair.public_key, NEON_TOKEN_MINT_ID)

        with open("evm_loader-keypair.json", "r") as key:
            secret_key = json.load(key)[:32]
            mint_authority = Keypair.from_secret_key(secret_key)

        trx = Transaction()
        trx.add(
            make_CreateAssociatedTokenIdempotent(
                operator_keypair.public_key, operator_keypair.public_key, NEON_TOKEN_MINT_ID
            ),
            spl.token.instructions.mint_to(
                MintToParams(
                    TOKEN_PROGRAM_ID,
                    NEON_TOKEN_MINT_ID,
                    token_pubkey,
                    mint_authority.public_key,
                    amount,
                )
            ),
            spl.token.instructions.approve(
                ApproveParams(
                    spl.token.constants.TOKEN_PROGRAM_ID,
                    token_pubkey,
                    balance_pubkey,
                    operator_keypair.public_key,
                    amount,
                )
            ),
            make_DepositV03(
                self.ether2bytes(ether_address),
                CHAIN_ID,
                balance_pubkey,
                contract_pubkey,
                NEON_TOKEN_MINT_ID,
                token_pubkey,
                evm_pool_key,
                spl.token.constants.TOKEN_PROGRAM_ID,
                operator_keypair.public_key,
                self.loader_id,
            ),
        )

        receipt = self.send_tx(trx, operator_keypair, mint_authority)

        return receipt

    def make_new_user(self, sender: Keypair) -> Caller:
        key = Keypair.generate()
        if self.get_solana_balance(key.public_key) == 0:
            self.request_airdrop(key.public_key, 1000 * 10**9, commitment=Confirmed)
        caller_ether = eth_keys.PrivateKey(key.secret_key[:32]).public_key.to_canonical_address()
        caller_solana = self.ether2program(caller_ether)[0]
        caller_balance = self.ether2balance(caller_ether)
        caller_token = get_associated_token_address(caller_balance, NEON_TOKEN_MINT_ID)

        if self.get_solana_balance(caller_balance) == 0:
            print(f"Create Neon account {caller_ether} for user {caller_balance}")
            self.create_balance_account(caller_ether, sender)

        print("Account solana address:", key.public_key)
        print(
            f"Account ether address: {caller_ether.hex()}",
        )
        print(f"Account solana address: {caller_balance}")
        return Caller(key, PublicKey(caller_solana), caller_balance, caller_ether, caller_token)

    def sent_token_from_solana_to_neon(self, solana_account, mint, neon_account, amount, chain_id):
        """Transfer any token from solana to neon transaction"""
        balance_pubkey = self.ether2balance(neon_account.address, chain_id)
        contract_pubkey = PublicKey(self.ether2program(neon_account.address)[0])
        associated_token_address = get_associated_token_address(solana_account.public_key, mint)
        authority_pool = PublicKey.find_program_address([b"Deposit"], self.loader_id)[0]

        pool = get_associated_token_address(authority_pool, mint)

        tx = Transaction(fee_payer=solana_account.public_key)
        tx.add(
            approve(
                ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=associated_token_address,
                    delegate=balance_pubkey,
                    owner=solana_account.public_key,
                    amount=amount,
                )
            )
        )

        tx.add(
            make_DepositV03(
                bytes.fromhex(neon_account.address[2:]),
                chain_id,
                balance_pubkey,
                contract_pubkey,
                mint,
                associated_token_address,
                pool,
                TOKEN_PROGRAM_ID,
                solana_account.public_key,
                self.loader_id,
            )
        )
        self.send_tx_and_check_status_ok(tx, solana_account)

    def deposit_wrapped_sol_from_solana_to_neon(self, solana_account, neon_account, chain_id, full_amount=None):
        if not full_amount:
            full_amount = int(0.1 * LAMPORT_PER_SOL)
        mint_pubkey = wSOL["address_spl"]
        ata_address = get_associated_token_address(solana_account.public_key, mint_pubkey)

        self.create_associate_token_acc(solana_account, solana_account, mint_pubkey)

        # wrap SOL
        wrap_sol_tx = make_wSOL(full_amount, solana_account.public_key, ata_address)
        self.send_tx_and_check_status_ok(wrap_sol_tx, solana_account)

        self.sent_token_from_solana_to_neon(solana_account, wSOL["address_spl"], neon_account, full_amount, chain_id)

    def deposit_neon_like_tokens_from_solana_to_neon(
        self,
        neon_mint,
        solana_account,
        neon_account,
        chain_id,
        operator_keypair,
        amount,
    ):
        self.mint_spl_to(neon_mint, solana_account, amount, operator_keypair)

        self.sent_token_from_solana_to_neon(
            solana_account,
            neon_mint,
            neon_account,
            amount,
            chain_id,
        )

    def create_operator_balance_account(self, operator_keypair, operator_ether, chain_id=CHAIN_ID):
        account = self.ether2operator_balance(operator_keypair, operator_ether, chain_id)
        trx = make_OperatorBalanceAccount(
            operator_keypair, account, self.ether2bytes(operator_ether), chain_id, self.loader_id
        )
        self.send_tx(trx, operator_keypair)
