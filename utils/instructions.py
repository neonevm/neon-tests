import typing as tp
from hashlib import sha256

from solana.keypair import Keypair
from solana.publickey import PublicKey
import solana.system_program as sp
from solana.transaction import AccountMeta, TransactionInstruction, Transaction

from utils.consts import COMPUTE_BUDGET_ID
from solana.system_program import SYS_PROGRAM_ID
from solana.sysvar import SYSVAR_RENT_PUBKEY
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from utils.types import TreasuryPool

DEFAULT_UNITS = 1_400_000
DEFAULT_HEAP_FRAME = 256 * 1024
DEFAULT_ADDITIONAL_FEE = 0


class ComputeBudget:
    @staticmethod
    def request_units(operator, units):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[AccountMeta(PublicKey(operator.public_key), is_signer=True, is_writable=False)],
            data=bytes.fromhex("02") + units.to_bytes(4, "little")
        )

    @staticmethod
    def request_heap_frame(operator, heap_frame):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[AccountMeta(PublicKey(operator.public_key), is_signer=True, is_writable=False)],
            data=bytes.fromhex("01") + heap_frame.to_bytes(4, "little")
        )

    @staticmethod
    def set_compute_units_price(price, operator):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[AccountMeta(PublicKey(operator.public_key), is_signer=True, is_writable=False)],
            data=bytes.fromhex("03") + price.to_bytes(8, "little")
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
            self.add(ComputeBudget.set_compute_units_price(compute_unit_price,  operator))


def make_WriteHolder(
    operator: PublicKey, evm_loader_id: PublicKey, holder_account: PublicKey, hash: bytes, offset: int, payload: bytes
):
    d = bytes([0x26]) + hash + offset.to_bytes(8, byteorder="little") + payload

    return TransactionInstruction(
        program_id=evm_loader_id,
        data=d,
        keys=[
            AccountMeta(pubkey=holder_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator, is_signer=True, is_writable=False),
        ],
    )


def make_ExecuteTrxFromInstruction(
    operator: Keypair,
    operator_balance: PublicKey,
    holder_address: PublicKey,
    evm_loader_id: PublicKey,
    treasury_address: PublicKey,
    treasury_buffer: bytes,
    message: bytes,
    additional_accounts: tp.List[PublicKey],
    system_program=sp.SYS_PROGRAM_ID,
    tag=0x3D
):
    data = bytes([tag]) + treasury_buffer + message
    print("make_ExecuteTrxFromInstruction accounts")
    print("Holder: ", holder_address)
    print("Operator: ", operator.public_key)
    print("Treasury: ", treasury_address)
    print("Operator balance: ", operator_balance)
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(system_program, is_signer=False, is_writable=True)
    ]
    for acc in additional_accounts:
        print("Additional acc ", acc)
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return TransactionInstruction(program_id=evm_loader_id, data=data, keys=accounts)


def make_ExecuteTrxFromAccount(
    operator: Keypair,
    operator_balance: PublicKey,
    evm_loader_id: PublicKey,
    holder_address: PublicKey,
    treasury_address: PublicKey,
    treasury_buffer: bytes,
    additional_accounts: tp.List[PublicKey],
    additional_signers: tp.List[Keypair] = None,
    system_program=sp.SYS_PROGRAM_ID,
    tag=0x33
):
    data = bytes([tag]) + treasury_buffer
    print("make_ExecuteTrxFromInstruction accounts")
    print("Operator: ", operator.public_key)
    print("Treasury: ", treasury_address)
    print("Operator eth solana: ", operator_balance)
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(system_program, is_signer=False, is_writable=True)
    ]
    for acc in additional_accounts:
        print("Additional acc ", acc)
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )
    if additional_signers:
        for acc in additional_signers:
            accounts.append(
                AccountMeta(acc.public_key, is_signer=True, is_writable=True),
            )
    return TransactionInstruction(program_id=evm_loader_id, data=data, keys=accounts)


def make_ExecuteTrxFromAccountDataIterativeOrContinue(
    index: int,
    step_count: int,
    operator: Keypair,
    operator_balance: PublicKey,
    evm_loader_id: PublicKey,
    holder_address: PublicKey,
    treasury,
    additional_accounts: tp.List[PublicKey],
    sys_program_id=sp.SYS_PROGRAM_ID,
    tag=0x35
):
    # 0x35 - TransactionStepFromAccount
    # 0x36 - TransactionStepFromAccountNoChainId
    data = tag.to_bytes(1, "little") + treasury.buffer + step_count.to_bytes(4, "little") + index.to_bytes(4, "little")
    print("make_ExecuteTrxFromAccountDataIterativeOrContinue accounts")
    print("Holder: ", holder_address)
    print("Operator: ", operator.public_key)
    print("Treasury: ", treasury.account)
    print("Operator eth solana: ", operator_balance)
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(sys_program_id, is_signer=False, is_writable=True)
    ]

    for acc in additional_accounts:
        print("Additional acc ", acc)
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return TransactionInstruction(program_id=evm_loader_id, data=data, keys=accounts)


def make_PartialCallOrContinueFromRawEthereumTX(
    index: int,
    step_count: int,
    instruction: bytes,
    operator: Keypair,
    operator_balance: PublicKey,
    evm_loader_id: PublicKey,
    storage_address: PublicKey,
    treasury: TreasuryPool,
    additional_accounts: tp.List[PublicKey],
    system_program=sp.SYS_PROGRAM_ID,
    tag=0x34  # TransactionStepFromInstruction
):
    data = bytes([tag]) + treasury.buffer + step_count.to_bytes(4, "little") + index.to_bytes(4, "little") + instruction

    accounts = [
        AccountMeta(pubkey=storage_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(system_program, is_signer=False, is_writable=True)
    ]
    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return TransactionInstruction(program_id=evm_loader_id, data=data, keys=accounts)


def make_Cancel(
    evm_loader_id: PublicKey,
    storage_address: PublicKey,
    operator: Keypair,
    operator_balance: PublicKey,
    hash: bytes,
    additional_accounts: tp.List[PublicKey],
):
    data = bytes([0x37]) + hash

    accounts = [
        AccountMeta(pubkey=storage_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
    ]

    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return TransactionInstruction(program_id=evm_loader_id, data=data, keys=accounts)


def make_DepositV03(
    ether_address: bytes,
    chain_id: int,
    balance_account: PublicKey,
    contract_account: PublicKey,
    mint: PublicKey,
    source: PublicKey,
    pool: PublicKey,
    token_program: PublicKey,
    operator_pubkey: PublicKey,
    evm_loader_id: PublicKey,
) -> TransactionInstruction:
    data = bytes([0x31]) + ether_address + chain_id.to_bytes(8, "little")

    accounts = [
        AccountMeta(pubkey=mint, is_signer=False, is_writable=True),
        AccountMeta(pubkey=source, is_signer=False, is_writable=True),
        AccountMeta(pubkey=pool, is_signer=False, is_writable=True),
        AccountMeta(pubkey=balance_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=contract_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=token_program, is_signer=False, is_writable=False),
        AccountMeta(pubkey=operator_pubkey, is_signer=True, is_writable=True),
        AccountMeta(pubkey=sp.SYS_PROGRAM_ID, is_signer=False, is_writable=False),
    ]

    return TransactionInstruction(program_id=evm_loader_id, data=data, keys=accounts)


def make_CreateAssociatedTokenIdempotent(payer: PublicKey, owner: PublicKey, mint: PublicKey) -> TransactionInstruction:
    """Creates a transaction instruction to create an associated token account.

    Returns:
        The instruction to create the associated token account.
    """
    associated_token_address = get_associated_token_address(owner, mint)
    return TransactionInstruction(
        data=bytes([1]),
        keys=[
            AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
            AccountMeta(pubkey=associated_token_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=owner, is_signer=False, is_writable=False),
            AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False)
        ],
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
    )


def make_CreateBalanceAccount(
    evm_loader_id: PublicKey,
    sender_pubkey: PublicKey,
    ether_address: bytes,
    account_pubkey: PublicKey,
    contract_pubkey: PublicKey,
    chain_id,
) -> TransactionInstruction:
    print("createBalanceAccount: {}".format(account_pubkey))

    data = bytes([0x30]) + ether_address + chain_id.to_bytes(8, "little")
    return TransactionInstruction(
        program_id=evm_loader_id,
        data=data,
        keys=[
            AccountMeta(pubkey=sender_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=sp.SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=account_pubkey, is_signer=False, is_writable=True),
            AccountMeta(pubkey=contract_pubkey, is_signer=False, is_writable=True)
        ],
    )


def make_SyncNative(account: PublicKey):
    keys = [AccountMeta(pubkey=account, is_signer=False, is_writable=True)]
    data = bytes.fromhex("11")
    return TransactionInstruction(keys=keys, program_id=TOKEN_PROGRAM_ID, data=data)


def make_CreateAccountWithSeed(funding, base, seed, lamports, space, program):
    created = PublicKey(sha256(bytes(base) + bytes(seed, "utf8") + bytes(program)).digest())
    print(f"Created: {created}")
    return sp.create_account_with_seed(
        sp.CreateAccountWithSeedParams(
            from_pubkey=funding,
            new_account_pubkey=created,
            base_pubkey=base,
            seed=seed,
            lamports=lamports,
            space=space,
            program_id=program,
        )
    )


def make_CreateHolderAccount(account, operator, seed, evm_loader_id):
    return TransactionInstruction(
        keys=[
            AccountMeta(pubkey=account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator, is_signer=True, is_writable=False),
        ],
        program_id=evm_loader_id,
        data=bytes.fromhex("24") + len(seed).to_bytes(8, "little") + seed,
    )

def make_wSOL(amount, solana_wallet, ata_address):
    tx = Transaction(fee_payer=solana_wallet)
    tx.add(sp.transfer(sp.TransferParams(solana_wallet, ata_address, amount)))
    tx.add(make_SyncNative(ata_address))

    return tx

def make_OperatorBalanceAccount(operator_keypair, operator_balance_pubkey, ether_bytes, chain_id, evm_loader_id):
    trx = Transaction()
    trx.add(TransactionInstruction(
        keys=[
            AccountMeta(pubkey=operator_keypair.public_key, is_signer=True, is_writable=True),
            AccountMeta(pubkey=sp.SYS_PROGRAM_ID, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator_balance_pubkey, is_signer=False, is_writable=True)
        ],
        program_id=evm_loader_id,
        data=bytes.fromhex("3A") + ether_bytes + chain_id.to_bytes(8, 'little')
    ))
    return trx


def get_compute_unit_price_eip_1559(
        gas_price: int,
        max_priority_fee_per_gas: int,
) -> int:
    """
    :return: micro lamports
    """
    cu_price = max(1, int(max_priority_fee_per_gas * 1_000_000 * 5000.0 / (gas_price * DEFAULT_UNITS)))
    return cu_price
