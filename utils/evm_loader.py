import json
import pathlib
import typing
from hashlib import sha256
from random import randrange
from typing import Union

import spl
import typing as tp

from eth_account.signers.local import LocalAccount
from eth_keys import keys as eth_keys
from eth_account.datastructures import SignedTransaction
from eth_utils import keccak
from solders.keypair import Keypair
from solders.pubkey import Pubkey
import solders.system_program as sp
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.rpc.responses import SendTransactionResp, GetTransactionResp
from spl.token.instructions import (
    get_associated_token_address,
    MintToParams,
    ApproveParams,
    approve,
)
from spl.token.constants import TOKEN_PROGRAM_ID

from integration.tests.neon_evm.utils.contract import get_contract_bin
from integration.tests.neon_evm.utils.ethereum import create_contract_address, make_deployment_transaction
from integration.tests.neon_evm.utils.neon_api_client import NeonApiClient
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text
from utils.scheduled_trx import ScheduledTransaction
from utils.neon_user import NeonUser
from integration.tests.neon_evm.utils.constants import TREASURY_POOL_SEED
from utils.consts import LAMPORT_PER_SOL, wSOL
from utils.helpers import ether2bytes
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
    make_ScheduledTransactionCreate,
    make_ScheduledTransactionStartFromAccount,
    make_ScheduledTransactionFinish,
    make_ScheduledTransactionDestroy,
    make_ScheduledTransactionStartFromInstruction,
    make_ScheduledTransactionCreateMultiple,
    make_ScheduledTransactionSkipFromInstruction,
    make_CreateAccountWithSeed,
    make_CreateHolderAccount,
    make_DeleteHolderAccount,
)
from utils.layouts import (
    BALANCE_ACCOUNT_LAYOUT,
    CONTRACT_ACCOUNT_LAYOUT,
    STORAGE_CELL_LAYOUT,
    OPERATOR_BALANCE_ACCOUNT_LAYOUT,
)
from utils.solana_client import SolanaClient
from utils.solana_logs_helper import decode_logs
from utils.types import Caller, Contract, TreasuryPool

EVM_STEPS = 500


class EvmLoader(SolanaClient):
    def __init__(
        self,
        program_id: str,
        endpoint: str,
        neon_chain_id: int,
        sol_chain_id: int,
        neon_token_mint_str: str,
    ) -> None:
        super().__init__(endpoint)
        EvmLoader.loader_id = Pubkey.from_string(program_id)
        self.loader_id = EvmLoader.loader_id
        self.chain_id = neon_chain_id
        self.sol_chain_id = sol_chain_id
        self.neon_token_mint_id = Pubkey.from_string(neon_token_mint_str)

    def create_balance_account(self, ether: Union[str, bytes], sender, chain_id: int | None = None) -> Pubkey:
        chain_id = chain_id or self.chain_id

        account_pubkey = self.ether2balance(ether, chain_id)
        if not self.account_exists(account_pubkey):
            contract_pubkey = Pubkey.from_string(self.ether2program(ether)[0])
            trx = Transaction()
            trx.add(
                make_CreateBalanceAccount(
                    self.loader_id, sender.pubkey(), ether2bytes(ether), account_pubkey, contract_pubkey, chain_id
                )
            )
            self.send_tx_and_check_status_ok(trx, sender)
        return account_pubkey

    def create_treasury_pool_address(self, pool_index):
        return Pubkey.find_program_address(
            [bytes(TREASURY_POOL_SEED, "utf8"), pool_index.to_bytes(4, "little")], self.loader_id
        )[0]

    def create_tree_account_address(self, neon_address, nonce, chain_id: int | None = None):
        chain_id = chain_id or self.sol_chain_id

        chain_id_bytes = chain_id.to_bytes(8, "little")
        seeds = [self.account_seed_version, b"TREE", neon_address, chain_id_bytes, nonce]
        return Pubkey.find_program_address(seeds, self.loader_id)[0]

    def create_get_authority_address(self):
        return Pubkey.find_program_address([b"Deposit"], self.loader_id)[0]

    def ether2operator_balance(
        self,
        keypair: Keypair,
        ether_address: Union[str, bytes],
        chain_id: int | None = None,
    ) -> Pubkey:
        chain_id = chain_id or self.chain_id

        address_bytes = ether2bytes(ether_address)
        key = bytes(keypair.pubkey())
        chain_id_bytes = chain_id.to_bytes(32, "big")
        return Pubkey.find_program_address(
            [self.account_seed_version, key, address_bytes, chain_id_bytes], self.loader_id
        )[0]

    def get_neon_nonce(self, account: Union[str, bytes], chain_id: int | None = None) -> int:
        chain_id = chain_id or self.chain_id
        solana_address = self.ether2balance(account, chain_id)
        if self.account_exists(solana_address):
            info: bytes = self.get_solana_account_data(solana_address, BALANCE_ACCOUNT_LAYOUT.sizeof())
            layout = BALANCE_ACCOUNT_LAYOUT.parse(info)
            return layout.trx_count
        else:
            return 0

    def get_solana_account_data(self, account: Union[str, Pubkey, Keypair], expected_length: int) -> bytes:
        if isinstance(account, Keypair):
            account = account.pubkey()
        info = self.get_account_info(account, commitment=Confirmed)
        info = info.value
        if info is None:
            raise Exception("Can't get information about {}".format(account))
        if len(info.data) < expected_length:
            print("len(data)({}) < expected_length({})".format(len(info.data), expected_length))
            raise Exception("Wrong data length for account data {}".format(account))
        return info.data

    def get_neon_balance(self, account: Union[str, bytes], chain_id: int | None = None) -> int:
        chain_id = chain_id or self.chain_id

        balance_address = self.ether2balance(account, chain_id)

        info: bytes = self.get_solana_account_data(balance_address, BALANCE_ACCOUNT_LAYOUT.sizeof())
        layout = BALANCE_ACCOUNT_LAYOUT.parse(info)

        return int.from_bytes(layout.balance, byteorder="little")

    def get_operator_neon_balance(self, operator: Keypair, chain_id: int | None = None) -> int:
        chain_id = chain_id or self.chain_id

        balance_address = self.get_operator_balance_pubkey(operator, chain_id)

        info: bytes = self.get_solana_account_data(balance_address, OPERATOR_BALANCE_ACCOUNT_LAYOUT.sizeof())
        layout = OPERATOR_BALANCE_ACCOUNT_LAYOUT.parse(info)

        return int.from_bytes(layout.balance, byteorder="little")

    def get_contract_account_revision(self, address):
        account_data = self.get_solana_account_data(address, CONTRACT_ACCOUNT_LAYOUT.sizeof())
        return CONTRACT_ACCOUNT_LAYOUT.parse(account_data).revision

    def get_data_account_revision(self, address):
        account_data = self.get_solana_account_data(address, STORAGE_CELL_LAYOUT.sizeof())
        return STORAGE_CELL_LAYOUT.parse(account_data).revision

    def write_transaction_to_holder_account(
        self,
        tx: Union[SignedTransaction, bytes],
        holder_account: Pubkey,
        operator: Keypair,
    ):
        offset = 0
        receipts = []
        if isinstance(tx, SignedTransaction):
            rest = tx.raw_transaction
            tx_hash = tx.hash
        else:
            tx_hash = keccak(tx)
            rest = tx
        while len(rest):
            (part, rest) = (rest[:920], rest[920:])
            trx = Transaction()
            trx.add(make_WriteHolder(operator.pubkey(), self.loader_id, holder_account, tx_hash, offset, part))
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
        items = Pubkey.find_program_address([self.account_seed_version, ether2bytes(ether)], self.loader_id)
        return str(items[0]), items[1]

    def ether2balance(self, address: tp.Union[str, bytes], chain_id: int | None = None) -> Pubkey:
        chain_id = chain_id or self.chain_id

        # get public key associated with chain_id for an address
        address_bytes = ether2bytes(address)

        chain_id_bytes = chain_id.to_bytes(32, "big")
        return Pubkey.find_program_address([self.account_seed_version, address_bytes, chain_id_bytes], self.loader_id)[
            0
        ]

    def get_operator_balance_pubkey(self, operator: Keypair, chain_id: int | None = None) -> Pubkey:
        chain_id = chain_id or self.chain_id

        operator_ether = eth_keys.PrivateKey(operator.secret()[:32]).public_key.to_canonical_address()
        return self.ether2operator_balance(operator, operator_ether, chain_id)

    def execute_trx_from_instruction(
        self,
        operator: Keypair,
        holder_acc: Pubkey,
        treasury_address: Pubkey,
        treasury_buffer: bytes,
        instruction: SignedTransaction,
        additional_accounts,
        signer: Keypair = None,
        system_program=sp.ID,
        compute_unit_price=None,
    ) -> GetTransactionResp:
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
                instruction.raw_transaction,
                additional_accounts,
                system_program,
            )
        )

        return self.send_tx(trx, signer)

    def execute_trx_from_account(
        self,
        operator: Keypair,
        holder_acc: Pubkey,
        treasury_address: Pubkey,
        treasury_buffer: bytes,
        additional_accounts,
        signer: Keypair,
        system_program=sp.ID,
    ) -> GetTransactionResp:
        operator_balance = self.get_operator_balance_pubkey(operator)

        print(f"operator_balance: {operator_balance=}")
        print(f"operator: {operator=}")
        print(f"holder_acc: {holder_acc=}")
        print(f"treasury_address: {treasury_address=}")
        print(f"treasury_buffer: {treasury_buffer=}")
        print(f"additional_accounts: {additional_accounts=}")

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
        holder_address: Pubkey,
        treasury_address: Pubkey,
        treasury_buffer: bytes,
        instruction: SignedTransaction,
        additional_accounts,
        signer: Keypair = None,
        system_program=sp.ID,
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
                instruction.raw_transaction,
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
        treasury_address: Pubkey,
        treasury_buffer: bytes,
        additional_accounts,
        signer: Keypair = None,
        additional_signers: typing.List[Keypair] = None,
        system_program=sp.ID,
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
        instruction: Union[SignedTransaction, bytes],
        additional_accounts,
        steps_count,
        signer: Keypair,
        system_program=sp.ID,
        index=0,
        compute_unit_price=None,
        tag=0x34,
    ) -> GetTransactionResp:
        trx = TransactionWithComputeBudget(operator, compute_unit_price=compute_unit_price)
        if isinstance(instruction, SignedTransaction):
            raw_trx = instruction.raw_transaction
        else:
            raw_trx = instruction
        trx.add(
            make_PartialCallOrContinueFromRawEthereumTX(
                index,
                steps_count,
                raw_trx,
                operator,
                operator_balance_pubkey,
                self.loader_id,
                storage_account,
                treasury,
                additional_accounts,
                system_program,
                tag,
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
        compute_unit_price=None,
        chain_id: int | None = None,
    ) -> GetTransactionResp:
        chain_id = chain_id or self.chain_id

        signer = operator if signer is None else signer
        operator_balance_pubkey = self.get_operator_balance_pubkey(operator, chain_id)
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
                compute_unit_price=compute_unit_price,
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
        system_program=sp.ID,
        compute_unit_price=None,
        tag=0x35,
    ) -> GetTransactionResp:
        trx = TransactionWithComputeBudget(operator, compute_unit_price=compute_unit_price)
        trx.add(
            make_ExecuteTrxFromAccountDataIterativeOrContinue(
                step_count=steps_count,
                operator=operator,
                operator_balance=operator_balance_pubkey,
                evm_loader_id=self.loader_id,
                holder_address=storage_account,
                treasury=treasury,
                additional_accounts=additional_accounts,
                sys_program_id=system_program,
                tag=tag,
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
        compute_unit_price=None,
        chain_id: int | None = None,
        check_invalid_revision=False,
    ) -> GetTransactionResp:
        chain_id = chain_id or self.chain_id

        signer = operator if signer is None else signer
        operator_balance_pubkey = self.get_operator_balance_pubkey(operator, chain_id)

        receipt = None
        done = False
        is_invalid_revision = False

        while not done:
            receipt = self.send_transaction_step_from_account(
                operator,
                operator_balance_pubkey,
                treasury,
                storage_account,
                additional_accounts,
                EVM_STEPS,
                signer,
                compute_unit_price=compute_unit_price,
            )

            if receipt.value.transaction.meta.err:
                raise AssertionError(f"Error in sol trx: {receipt}")
            for log in receipt.value.transaction.meta.log_messages:
                if "exit_status" in log:
                    done = True
                    break
                if "ExitError" in log:
                    raise AssertionError(f"EVM Return error in logs: {receipt}")
            if check_invalid_revision:
                if "INVALID_REVISION" in decode_logs(receipt.value.transaction.meta.log_messages):
                    is_invalid_revision = True

        if check_invalid_revision and not is_invalid_revision:
            raise AssertionError("INVALID_REVISION not in logs")
        return receipt

    def execute_transaction_steps_from_account_no_chain_id(
        self, operator: Keypair, treasury, storage_account, additional_accounts, signer: Keypair = None
    ) -> GetTransactionResp:
        signer = operator if signer is None else signer
        operator_balance_pubkey = self.get_operator_balance_pubkey(operator)
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
            )

            if receipt.value.transaction.meta.err:
                raise AssertionError(f"Can't deploy contract: {receipt.value.transaction.meta.err}")
            for log in receipt.value.transaction.meta.log_messages:
                if "exit_status" in log:
                    done = True
                    break
                if "ExitError" in log:
                    raise AssertionError(f"EVM Return error in logs: {receipt}")

        return receipt

    def deposit_neon(
        self, operator_keypair: Keypair, ether_address: Union[str, bytes], amount: int
    ) -> GetTransactionResp:
        balance_pubkey = self.ether2balance(ether_address)
        contract_pubkey = Pubkey.from_string(self.ether2program(ether_address)[0])

        evm_token_authority = Pubkey.find_program_address([b"Deposit"], self.loader_id)[0]
        evm_pool_key = get_associated_token_address(evm_token_authority, self.neon_token_mint_id)

        token_pubkey = get_associated_token_address(operator_keypair.pubkey(), self.neon_token_mint_id)

        with open("evm_loader-keypair.json", "r") as key:
            secret_key = json.load(key)
            mint_authority = Keypair.from_bytes(secret_key)

        trx = Transaction()
        trx.add(
            make_CreateAssociatedTokenIdempotent(
                operator_keypair.pubkey(), operator_keypair.pubkey(), self.neon_token_mint_id
            ),
            spl.token.instructions.mint_to(
                MintToParams(
                    TOKEN_PROGRAM_ID,
                    self.neon_token_mint_id,
                    token_pubkey,
                    mint_authority.pubkey(),
                    amount,
                )
            ),
            spl.token.instructions.approve(
                ApproveParams(
                    spl.token.constants.TOKEN_PROGRAM_ID,
                    token_pubkey,
                    balance_pubkey,
                    operator_keypair.pubkey(),
                    amount,
                )
            ),
            make_DepositV03(
                ether2bytes(ether_address),
                self.chain_id,
                balance_pubkey,
                contract_pubkey,
                self.neon_token_mint_id,
                token_pubkey,
                evm_pool_key,
                spl.token.constants.TOKEN_PROGRAM_ID,
                operator_keypair.pubkey(),
                self.loader_id,
            ),
        )

        receipt = self.send_tx(trx, operator_keypair, mint_authority)

        return receipt

    def make_new_user(self, sender: Keypair) -> Caller:
        key = Keypair()
        if self.get_solana_balance(key.pubkey()) == 0:
            self.request_airdrop(key.pubkey(), 1000 * 10**9, commitment=Confirmed)
        caller_ether = eth_keys.PrivateKey(key.secret()[:32]).public_key.to_canonical_address()
        caller_solana = self.ether2program(caller_ether)[0]
        caller_balance = self.ether2balance(caller_ether)
        caller_token = get_associated_token_address(caller_balance, self.neon_token_mint_id)

        if self.get_solana_balance(caller_balance) == 0:
            print(f"Create Neon account {caller_ether.hex()} for user {caller_balance}")
            self.create_balance_account(caller_ether, sender)

        print("Account solana address:", key.pubkey())
        print(
            f"Account ether address: {caller_ether.hex()}",
        )
        print(f"Account solana address: {caller_balance}")
        return Caller(key, Pubkey.from_string(caller_solana), caller_balance, caller_ether, caller_token)

    def sent_token_from_solana_to_neon(self, solana_account, mint, neon_account, amount, chain_id):
        """Transfer any token from solana to neon transaction"""
        if isinstance(neon_account, LocalAccount):
            neon_account = neon_account.address
        balance_pubkey = self.ether2balance(neon_account, chain_id)
        contract_pubkey = Pubkey.from_string(self.ether2program(neon_account)[0])
        associated_token_address = get_associated_token_address(solana_account.pubkey(), mint)
        authority_pool = Pubkey.find_program_address([b"Deposit"], self.loader_id)[0]
        pool = get_associated_token_address(authority_pool, mint)
        tx = Transaction(fee_payer=solana_account.pubkey())
        tx.add(
            approve(
                ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=associated_token_address,
                    delegate=balance_pubkey,
                    owner=solana_account.pubkey(),
                    amount=amount,
                )
            )
        )

        tx.add(
            make_DepositV03(
                bytes.fromhex(neon_account[2:]),
                chain_id,
                balance_pubkey,
                contract_pubkey,
                mint,
                associated_token_address,
                pool,
                TOKEN_PROGRAM_ID,
                solana_account.pubkey(),
                self.loader_id,
            )
        )
        self.send_tx_and_check_status_ok(tx, solana_account)

    def deposit_wrapped_sol_from_solana_to_neon(self, solana_account, neon_account, full_amount=None):
        if not full_amount:
            full_amount = int(0.1 * LAMPORT_PER_SOL)
        mint_pubkey = wSOL["address_spl"]
        ata_address = get_associated_token_address(solana_account.pubkey(), mint_pubkey)

        self.create_associate_token_acc(solana_account, solana_account, mint_pubkey)

        # wrap SOL
        wrap_sol_tx = make_wSOL(full_amount, solana_account.pubkey(), ata_address)
        self.send_tx_and_check_status_ok(wrap_sol_tx, solana_account)

        self.sent_token_from_solana_to_neon(
            solana_account, wSOL["address_spl"], neon_account, full_amount, self.sol_chain_id
        )

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

    def create_operator_balance_account(self, operator_keypair, operator_ether, chain_id: int | str | None = ""):
        if chain_id == "":
            chain_id = self.chain_id

        account = self.ether2operator_balance(operator_keypair, operator_ether, chain_id)
        trx = make_OperatorBalanceAccount(
            operator_keypair, account, ether2bytes(operator_ether), chain_id, self.loader_id
        )
        self.send_tx(trx, operator_keypair)

    def create_tree_account(self, neon_user: NeonUser, treasury, transaction, mint, chain_id: int | str | None = ""):
        if chain_id == "":
            chain_id = self.sol_chain_id

        payer_nonce = self.get_neon_nonce(neon_user.neon_address, chain_id).to_bytes(8, "little")
        authority_pool = self.create_get_authority_address()
        tree_account = self.create_tree_account_address(neon_user.neon_address, payer_nonce, chain_id)
        pool = get_associated_token_address(authority_pool, mint)

        trx = Transaction()
        balance_account = self.create_balance_account(neon_user.neon_address, neon_user.solana_account, chain_id)
        trx.add(
            make_ScheduledTransactionCreate(
                neon_user.solana_account, balance_account, treasury, tree_account, pool, transaction, self.loader_id
            )
        )
        self.send_tx(trx, neon_user.solana_account)
        return tree_account

    def create_tree_account_multiple(
        self, neon_user, treasury, tree_account_create_data, mint: Pubkey, payer_nonce=None, chain_id: int | None = ""
    ):
        if chain_id == "":
            chain_id = self.sol_chain_id
        if not payer_nonce:
            payer_nonce = self.get_neon_nonce(neon_user.neon_address, chain_id).to_bytes(8, "little")
        else:
            payer_nonce = payer_nonce.to_bytes(8, "little")
        authority_pool = self.create_get_authority_address()
        tree_account = self.create_tree_account_address(neon_user.neon_address, payer_nonce, chain_id)
        pool = get_associated_token_address(authority_pool, mint)

        trx = Transaction()
        balance_account = self.create_balance_account(neon_user.neon_address, neon_user.solana_account, chain_id)
        trx.add(
            make_ScheduledTransactionCreateMultiple(
                neon_user.solana_account,
                balance_account,
                treasury,
                tree_account,
                pool,
                tree_account_create_data,
                self.loader_id,
            )
        )
        self.send_tx_and_check_status_ok(trx, neon_user.solana_account)
        return tree_account

    def start_scheduled_trx_from_account(
        self, index, operator, holder, tree_account, additional_accounts, chain_id: int | None = ""
    ):
        if chain_id == "":
            chain_id = self.sol_chain_id

        operator_balance = self.get_operator_balance_pubkey(operator, chain_id)
        trx = TransactionWithComputeBudget(operator, compute_unit_price=1000000)
        trx.add(
            make_ScheduledTransactionStartFromAccount(
                index, operator, operator_balance, self.loader_id, holder, tree_account, additional_accounts
            )
        )
        return self.send_tx(trx, operator)

    def start_scheduled_trx_from_instruction(
        self,
        neon_trx: ScheduledTransaction,
        operator,
        holder,
        tree_account,
        additional_accounts,
        chain_id: int | str | None = "",
    ):
        if chain_id == "":
            chain_id = self.sol_chain_id

        operator_balance = self.get_operator_balance_pubkey(operator, chain_id)
        trx = TransactionWithComputeBudget(operator, compute_unit_price=1000000)
        trx.add(
            make_ScheduledTransactionStartFromInstruction(
                neon_trx.index,
                neon_trx.encode(),
                holder,
                tree_account,
                self.loader_id,
                operator,
                operator_balance,
                additional_accounts,
            )
        )
        return self.send_tx(trx, operator)

    def execute_scheduled_trx_from_account(
        self,
        index,
        operator,
        holder,
        tree_account,
        treasury,
        additional_accounts,
        chain_id: int | str | None = "",
        compute_unit_price=None,
    ):
        if chain_id == "":
            chain_id = self.sol_chain_id

        self.start_scheduled_trx_from_account(index, operator, holder, tree_account, additional_accounts, chain_id)
        return self.execute_transaction_steps_from_account(
            operator, treasury, holder, additional_accounts, chain_id=chain_id, compute_unit_price=compute_unit_price
        )

    def execute_scheduled_trx_from_instruction(
        self,
        trx: ScheduledTransaction,
        operator,
        holder,
        tree_account,
        treasury,
        additional_accounts,
        chain_id: int | str | None = "",
    ):
        if chain_id == "":
            chain_id = self.sol_chain_id

        self.start_scheduled_trx_from_instruction(trx, operator, holder, tree_account, additional_accounts, chain_id)
        self.execute_transaction_steps_from_instruction(
            operator, treasury, holder, trx.encode(), additional_accounts, compute_unit_price=15, chain_id=chain_id
        )

    def finish_scheduled_trx(self, operator, tree_account, holder_account, chain_id: int | str | None = ""):
        if chain_id == "":
            chain_id = self.sol_chain_id

        trx = TransactionWithComputeBudget(operator, compute_unit_price=1000000)
        operator_balance = self.get_operator_balance_pubkey(operator, chain_id)
        trx.add(
            make_ScheduledTransactionFinish(
                operator.pubkey(), operator_balance, self.loader_id, holder_account, tree_account
            )
        )
        return self.send_tx(trx, operator)

    def skip_scheduled_trx_from_instruction(
        self, neon_trx, operator, tree_account, holder_account, chain_id: int | str | None = ""
    ):
        if chain_id == "":
            chain_id = self.sol_chain_id

        operator_balance_pubkey = self.get_operator_balance_pubkey(operator, chain_id)
        trx = TransactionWithComputeBudget(operator, compute_unit_price=1000000)
        trx.add(
            make_ScheduledTransactionSkipFromInstruction(
                neon_trx.index,
                neon_trx.encode(),
                operator,
                operator_balance_pubkey,
                holder_account,
                tree_account,
                self.loader_id,
            )
        )
        return self.send_tx(trx, operator)

    def destroy_tree_account(
        self, neon_user: NeonUser, treasury, tree_account, chain_id: int | None = ""
    ) -> GetTransactionResp:
        if chain_id == "":
            chain_id = self.sol_chain_id

        trx = Transaction()

        trx.add(
            make_ScheduledTransactionDestroy(
                neon_user.solana_account.pubkey(),
                neon_user.get_balance_account(chain_id),
                treasury,
                tree_account,
                self.loader_id,
            )
        )
        return self.send_tx(trx, neon_user.solana_account)

    def deploy_contract(
        self,
        operator: Keypair,
        user: Caller,
        contract_file_name: tp.Union[pathlib.Path, str],
        neon_api_client: NeonApiClient,
        treasury_pool: TreasuryPool,
        chain_id: int | str | None = "",
        value: int = 0,
        encoded_args=None,
        contract_name: tp.Optional[str] = None,
        version: str = "0.7.6",
    ) -> Contract:
        if chain_id == "":
            chain_id = self.chain_id

        contract_code = get_contract_bin(contract_file_name, contract_name=contract_name, version=version)
        if encoded_args is None:
            encoded_args = b""

        emulate_result = neon_api_client.emulate(
            user.eth_address.hex(),
            contract=None,
            data=contract_code + encoded_args.hex(),
            chain_id=chain_id,
            value=hex(value),
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        contract: Contract = create_contract_address(user, self, chain_id)
        holder_acc = self.create_holder(operator)
        signed_tx = make_deployment_transaction(
            self,
            user,
            contract_file_name,
            contract_name,
            encoded_args=encoded_args,
            value=value,
            version=version,
            chain_id=chain_id,
        )
        self.write_transaction_to_holder_account(signed_tx, holder_acc, operator)

        resp = self.execute_transaction_steps_from_account(
            operator, treasury_pool, holder_acc, additional_accounts, chain_id=chain_id
        )
        check_transaction_logs_have_text(solana_client=self, trx=resp, text="exit_status=0x12")
        return contract

    def create_holder(
        self,
        signer: Keypair,
        seed: str = None,
        size: int = None,
        fund: int = None,
        storage: Pubkey = None,
    ) -> Pubkey:
        if size is None:
            size = 128 * 1024
        if fund is None:
            fund = 10**9
        if seed is None:
            seed = str(randrange(100000000000))
        if storage is None:
            storage = Pubkey.from_bytes(
                sha256(bytes(signer.pubkey()) + bytes(seed, "utf8") + bytes(self.loader_id)).digest()
            )

        print(f"Create holder account with seed: {seed}")

        if self.get_solana_balance(storage) == 0:
            trx = Transaction()
            trx.add(
                make_CreateAccountWithSeed(signer.pubkey(), signer.pubkey(), seed, fund, size, self.loader_id),
                make_CreateHolderAccount(storage, signer.pubkey(), bytes(seed, "utf8"), self.loader_id),
            )
            self.send_tx(trx, signer)
            return storage
        else:
            self.create_holder(signer, seed, size, fund, storage)

    def delete_holder(self, del_key: Pubkey, acc: Keypair, signer: Keypair):
        trx = Transaction()
        trx.add(make_DeleteHolderAccount(acc.pubkey(), del_key, self.loader_id))
        return self.send_tx(trx, signer)
