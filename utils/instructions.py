import functools
import typing as tp
from hashlib import sha256

import solders.system_program as sp
from solana.transaction import AccountMeta, Instruction, Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import ID as SYS_PROGRAM_ID
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from utils.consts import COMPUTE_BUDGET_ID, InstructionTags, COUNTER_ID
from utils.types import TreasuryPool
from .logger import log_text_to_allure_and_stdout
from .metaplex import SYSVAR_RENT_PUBKEY

DEFAULT_UNITS = 1_400_000
DEFAULT_HEAP_FRAME = 256 * 1024
DEFAULT_ADDITIONAL_FEE = 0


class ComputeBudget:
    @staticmethod
    def request_units(operator: Keypair, units):
        return Instruction(
            program_id=COMPUTE_BUDGET_ID,
            accounts=[AccountMeta(operator.pubkey(), is_signer=True, is_writable=False)],
            data=bytes.fromhex("02") + units.to_bytes(4, "little"),
        )

    @staticmethod
    def request_heap_frame(operator: Keypair, heap_frame):
        return Instruction(
            program_id=COMPUTE_BUDGET_ID,
            accounts=[AccountMeta(operator.pubkey(), is_signer=True, is_writable=False)],
            data=bytes.fromhex("01") + heap_frame.to_bytes(4, "little"),
        )

    @staticmethod
    def set_compute_units_price(price, operator: Keypair):
        return Instruction(
            program_id=COMPUTE_BUDGET_ID,
            accounts=[AccountMeta(operator.pubkey(), is_signer=True, is_writable=False)],
            data=bytes.fromhex("03") + price.to_bytes(8, "little"),
        )


class TransactionWithComputeBudget(Transaction):
    def __init__(
        self,
        operator: Keypair,
        units=DEFAULT_UNITS,
        heap_frame=DEFAULT_HEAP_FRAME,
        compute_unit_price=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        if units:
            self.add(ComputeBudget.request_units(operator, units))

        if heap_frame:
            self.add(ComputeBudget.request_heap_frame(operator, heap_frame))
        if compute_unit_price:
            self.add(ComputeBudget.set_compute_units_price(compute_unit_price, operator))


def log_instruction_fields(title_prefix: str = ""):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if hasattr(result, "program_id") and hasattr(result, "data") and hasattr(result, "accounts"):
                program_id = result.program_id
                data_hex = result.data.hex()
                accounts = result.accounts

                log_text = f"Program ID: {program_id}\n" f"Data (hex): {data_hex}\n" f"Accounts:\n"
                for acc in accounts:
                    log_text += f"  - pubkey: {acc.pubkey}, signer: {acc.is_signer}, writable: {acc.is_writable}\n"

                log_text_to_allure_and_stdout(f"{title_prefix}Instruction Info", log_text)
            return result

        return wrapper

    return decorator


@log_instruction_fields("holder_write")
def make_holder_write(
    operator: Pubkey, evm_loader_id: Pubkey, holder_account: Pubkey, hash_: bytes, offset: int, payload: bytes
):
    d = InstructionTags.HOLDER_WRITE + hash_ + offset.to_bytes(8, byteorder="little") + payload

    return Instruction(
        program_id=evm_loader_id,
        data=d,
        accounts=[
            AccountMeta(pubkey=holder_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator, is_signer=True, is_writable=False),
        ],
    )


@log_instruction_fields("transaction_execute_from_instruction")
def make_transaction_execute_from_instruction(
    operator: Keypair,
    operator_balance: Pubkey,
    holder_address: Pubkey,
    evm_loader_id: Pubkey,
    treasury_address: Pubkey,
    treasury_buffer: bytes,
    message: bytes,
    additional_accounts: tp.List[Pubkey],
    system_program=sp.ID,
    tag=InstructionTags.TRANSACTION_EXECUTE_FROM_INSTRUCTION,
):
    data = tag + treasury_buffer + message
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(system_program, is_signer=False, is_writable=True),
    ]
    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("transaction_execute_from_account")
def make_transaction_execute_from_account(
    operator: Keypair,
    operator_balance: Pubkey,
    evm_loader_id: Pubkey,
    holder_address: Pubkey,
    treasury_address: Pubkey,
    treasury_buffer: bytes,
    additional_accounts: tp.List[Pubkey],
    additional_signers: tp.List[Keypair] = None,
    system_program=sp.ID,
    tag=InstructionTags.TRANSACTION_EXECUTE_FROM_ACCOUNT,
):
    data = tag + treasury_buffer
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(system_program, is_signer=False, is_writable=True),
    ]
    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )
    if additional_signers:
        for acc in additional_signers:
            accounts.append(
                AccountMeta(acc.pubkey(), is_signer=True, is_writable=True),
            )
    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("transaction_step_from_account")
def make_transaction_step_from_account(
    step_count: int,
    operator: Keypair,
    operator_balance: Pubkey,
    evm_loader_id: Pubkey,
    holder_address: Pubkey,
    treasury,
    additional_accounts: tp.List[Pubkey],
    additional_signers: tp.List[Keypair] = None,
    sys_program_id=sp.ID,
    tag: InstructionTags = InstructionTags.TRANSACTION_STEP_FROM_ACCOUNT,
):
    # can be used:
    # 0x35 - TransactionStepFromAccount
    # 0x36 - TransactionStepFromAccountNoChainId

    data = tag + treasury.buffer + step_count.to_bytes(4, "little")
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(sys_program_id, is_signer=False, is_writable=True),
    ]

    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )
    if additional_signers:
        for acc in additional_signers:
            accounts.append(
                AccountMeta(acc.pubkey(), is_signer=True, is_writable=True),
            )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("transaction_step_from_instruction")
def make_transaction_step_from_instruction(
    index: int,
    step_count: int,
    instruction: bytes,
    operator: Keypair,
    operator_balance: Pubkey,
    evm_loader_id: Pubkey,
    storage_address: Pubkey,
    treasury: TreasuryPool,
    additional_accounts: tp.List[Pubkey],
    system_program=sp.ID,
    tag: InstructionTags = InstructionTags.TRANSACTION_STEP_FROM_INSTRUCTION,
):
    data = tag + treasury.buffer + step_count.to_bytes(4, "little") + index.to_bytes(4, "little") + instruction

    accounts = [
        AccountMeta(pubkey=storage_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(system_program, is_signer=False, is_writable=True),
    ]
    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("Cancel")
def make_cancel(
    evm_loader_id: Pubkey,
    storage_address: Pubkey,
    operator: Keypair,
    operator_balance: Pubkey,
    hash_: bytes,
    additional_accounts: tp.List[Pubkey],
):
    data = InstructionTags.CANCEL + hash_

    accounts = [
        AccountMeta(pubkey=storage_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
    ]

    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("Deposit")
def make_deposit(
    ether_address: bytes,
    chain_id: int,
    balance_account: Pubkey,
    contract_account: Pubkey,
    mint: Pubkey,
    source: Pubkey,
    pool: Pubkey,
    token_program: Pubkey,
    operator_pubkey: Pubkey,
    evm_loader_id: Pubkey,
) -> Instruction:
    data = InstructionTags.DEPOSIT + ether_address + chain_id.to_bytes(8, "little")

    accounts = [
        AccountMeta(pubkey=mint, is_signer=False, is_writable=True),
        AccountMeta(pubkey=source, is_signer=False, is_writable=True),
        AccountMeta(pubkey=pool, is_signer=False, is_writable=True),
        AccountMeta(pubkey=balance_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=contract_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=token_program, is_signer=False, is_writable=False),
        AccountMeta(pubkey=operator_pubkey, is_signer=True, is_writable=True),
        AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
    ]

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("create_associated_token_idempotent")
def make_create_associated_token_idempotent(payer: Pubkey, owner: Pubkey, mint: Pubkey) -> Instruction:  # todo what
    """Creates a transaction instruction to create an associated token account.

    Returns:
        The instruction to create the associated token account.
    """
    associated_token_address = get_associated_token_address(owner, mint)
    return Instruction(
        data=bytes([1]),
        accounts=[
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=associated_token_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=False, is_writable=False),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
        ],
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
    )


@log_instruction_fields("account_create_balance")
def make_account_create_balance(
    evm_loader_id: Pubkey,
    sender_pubkey: Pubkey,
    ether_address: bytes,
    account_pubkey: Pubkey,
    contract_pubkey: Pubkey,
    chain_id,
) -> Instruction:
    data = InstructionTags.ACCOUNT_CREATE_BALANCE + ether_address + chain_id.to_bytes(8, "little")
    return Instruction(
        program_id=evm_loader_id,
        data=data,
        accounts=[
            AccountMeta(pubkey=sender_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=account_pubkey, is_signer=False, is_writable=True),
            AccountMeta(pubkey=contract_pubkey, is_signer=False, is_writable=True),
        ],
    )


@log_instruction_fields("make_sync_native")
def make_sync_native(account: Pubkey):  # todo what
    keys = [AccountMeta(pubkey=account, is_signer=False, is_writable=True)]
    data = bytes.fromhex("11")
    return Instruction(accounts=keys, program_id=TOKEN_PROGRAM_ID, data=data)


@log_instruction_fields("create_account_with_seed")
def make_create_account_with_seed(funding, base, seed, lamports, space, program):  # todo
    created = Pubkey(sha256(bytes(base) + bytes(seed, "utf8") + bytes(program)).digest())
    return sp.create_account_with_seed(
        sp.CreateAccountWithSeedParams(
            from_pubkey=funding,
            to_pubkey=created,
            base=base,
            seed=seed,
            lamports=lamports,
            space=space,
            owner=program,
        )
    )


@log_instruction_fields("account_create_holder")
def make_account_create_holder(account, operator, seed, evm_loader_id):
    return Instruction(
        accounts=[
            AccountMeta(pubkey=account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator, is_signer=True, is_writable=False),
        ],
        program_id=evm_loader_id,
        data=InstructionTags.HOLDER_CREATE + len(seed).to_bytes(8, "little") + seed,
    )


@log_instruction_fields("WSOL")
def make_wSOL(amount, solana_wallet, ata_address):
    tx = Transaction(fee_payer=solana_wallet)
    tx.add(sp.transfer(sp.TransferParams(from_pubkey=solana_wallet, to_pubkey=ata_address, lamports=amount)))
    tx.add(make_sync_native(ata_address))
    return tx


@log_instruction_fields("operator_create_balance")
def make_operator_create_balance(operator_keypair, operator_balance_pubkey, ether_bytes, chain_id, evm_loader_id):
    tag = InstructionTags.OPERATOR_BALANCE_CREATE
    trx = Transaction()
    trx.add(
        Instruction(
            accounts=[
                AccountMeta(pubkey=operator_keypair.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=True),
                AccountMeta(pubkey=operator_balance_pubkey, is_signer=False, is_writable=True),
            ],
            program_id=evm_loader_id,
            data=tag + ether_bytes + chain_id.to_bytes(8, "little"),
        )
    )
    return trx


@log_instruction_fields("ScheduledTransactionCreate")
def make_scheduled_transaction_create(signer, balance_pubkey, treasury, tree_account, pool, msg, evm_loader_id):
    tag = InstructionTags.SCHEDULED_TRANSACTION_CREATE
    data = tag + treasury.buffer + msg
    trx = Transaction()
    trx.add(
        Instruction(
            accounts=[
                AccountMeta(pubkey=signer.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=balance_pubkey, is_signer=False, is_writable=True),
                AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
                AccountMeta(pubkey=tree_account, is_signer=False, is_writable=True),
                AccountMeta(pubkey=pool, is_signer=False, is_writable=True),
                AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
            ],
            program_id=evm_loader_id,
            data=data,
        )
    )
    return trx


@log_instruction_fields("scheduled_transaction_create_multiple")
def make_scheduled_transaction_create_multiple(
    signer, balance_pubkey, treasury, tree_account, pool, msg, evm_loader_id
):
    tag = InstructionTags.SCHEDULED_TRANSACTION_CREATE_MULTIPLE
    data = tag + treasury.buffer + msg
    trx = Transaction()
    trx.add(
        Instruction(
            accounts=[
                AccountMeta(pubkey=signer.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=balance_pubkey, is_signer=False, is_writable=True),
                AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
                AccountMeta(pubkey=tree_account, is_signer=False, is_writable=True),
                AccountMeta(pubkey=pool, is_signer=False, is_writable=True),
                AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
            ],
            program_id=evm_loader_id,
            data=data,
        )
    )
    return trx


@log_instruction_fields("scheduled_transaction_start_from_account")
def make_scheduled_transaction_start_from_account(
    index: int,
    operator: Keypair,
    operator_balance: Pubkey,
    evm_loader_id: Pubkey,
    holder_address: Pubkey,
    tree_account: Pubkey,
    additional_accounts: tp.List[Pubkey],
):
    tag = InstructionTags.SCHEDULED_TRANSACTION_START_FROM_ACCOUNT
    data = tag + index.to_bytes(4, "little")
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=tree_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
    ]

    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("scheduled_transaction_start_from_instruction")
def make_scheduled_transaction_start_from_instruction(
    index, neon_trx, holder_address, tree_account, evm_loader_id, operator, operator_balance, additional_accounts
):
    tag = InstructionTags.SCHEDULED_TRANSACTION_START_FROM_INSTRUCTION
    data = tag + index.to_bytes(4, "little") + neon_trx
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=tree_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
    ]

    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("scheduled_transaction_destroy")
def make_scheduled_transaction_destroy(
    signer: Pubkey, balance_account: Pubkey, treasury: TreasuryPool, tree_account: Pubkey, evm_loader_id: Pubkey
):
    data = InstructionTags.SCHEDULED_TRANSACTION_DESTROY + treasury.buffer
    accounts = [
        AccountMeta(pubkey=signer, is_signer=True, is_writable=True),
        AccountMeta(pubkey=balance_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=tree_account, is_signer=False, is_writable=True),
    ]
    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("scheduled_transaction_finish")
def make_scheduled_transaction_finish(
    operator: Pubkey, operator_balance: Pubkey, evm_loader_id: Pubkey, holder_address: Pubkey, tree_account: Pubkey
):
    data = InstructionTags.SCHEDULED_TRANSACTION_FINISH
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=tree_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator, is_signer=True, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
    ]
    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("scheduled_transaction_skip_from_instruction")
def make_scheduled_transaction_skip_from_instruction(
    index: int,
    neon_trx: bytes,
    operator: Keypair,
    operator_balance: Pubkey,
    holder_address: Pubkey,
    tree_account: Pubkey,
    evm_loader_id: Pubkey,
):
    data = InstructionTags.SCHEDULED_TRANSACTION_SKIP_FROM_INSTRUCTION
    data += index.to_bytes(4, "little") + neon_trx
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=tree_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
    ]
    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


@log_instruction_fields("make_delete_holder_account")
def make_delete_holder_account(signer: Pubkey, holder_account: Pubkey, evm_loader_id):
    return Instruction(
        program_id=evm_loader_id,
        data=InstructionTags.HOLDER_DELETE,
        accounts=[
            AccountMeta(pubkey=holder_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=signer, is_signer=True, is_writable=True),
        ],
    )


def make_increment_counter(counter_resource_address: Pubkey) -> Instruction:
    return Instruction(
        program_id=COUNTER_ID,
        accounts=[
            AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
        ],
        data=bytes([0x1]),
    )
