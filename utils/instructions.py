import typing as tp
from hashlib import sha256

from solders.keypair import Keypair
from solders.pubkey import Pubkey
import solders.system_program as sp
from solana.transaction import AccountMeta, Instruction, Transaction

from utils.consts import COMPUTE_BUDGET_ID
from solders.system_program import ID as SYS_PROGRAM_ID
from .metaplex import SYSVAR_RENT_PUBKEY
from spl.token.constants import ASSOCIATED_TOKEN_PROGRAM_ID, TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from utils.types import TreasuryPool

DEFAULT_UNITS = 1_400_000
DEFAULT_HEAP_FRAME = 256 * 1024
DEFAULT_ADDITIONAL_FEE = 0


class ComputeBudget:
    @staticmethod
    def request_units(operator: Keypair, units):
        return Instruction(
            program_id=COMPUTE_BUDGET_ID,
            accounts=[AccountMeta(operator.pubkey(), is_signer=True, is_writable=False)],
            data=bytes.fromhex("02") + units.to_bytes(4, "little")
        )

    @staticmethod
    def request_heap_frame(operator: Keypair, heap_frame):
        return Instruction(
            program_id=COMPUTE_BUDGET_ID,
            accounts=[AccountMeta(operator.pubkey(), is_signer=True, is_writable=False)],
            data=bytes.fromhex("01") + heap_frame.to_bytes(4, "little")
        )

    @staticmethod
    def set_compute_units_price(price, operator: Keypair):
        return Instruction(
            program_id=COMPUTE_BUDGET_ID,
            accounts=[AccountMeta(operator.pubkey(), is_signer=True, is_writable=False)],
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
    operator: Pubkey, evm_loader_id: Pubkey, holder_account: Pubkey, hash_: bytes, offset: int, payload: bytes
):
    d = bytes([0x26]) + hash_ + offset.to_bytes(8, byteorder="little") + payload

    return Instruction(
        program_id=evm_loader_id,
        data=d,
        accounts=[
            AccountMeta(pubkey=holder_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator, is_signer=True, is_writable=False),
        ],
    )


def make_ExecuteTrxFromInstruction(
    operator: Keypair,
    operator_balance: Pubkey,
    holder_address: Pubkey,
    evm_loader_id: Pubkey,
    treasury_address: Pubkey,
    treasury_buffer: bytes,
    message: bytes,
    additional_accounts: tp.List[Pubkey],
    system_program=sp.ID,
    tag=0x3D
):
    data = bytes([tag]) + treasury_buffer + message
    print("make_ExecuteTrxFromInstruction accounts")
    print("Holder: ", holder_address)
    print("Operator: ", operator.pubkey())
    print("Treasury: ", treasury_address)
    print("Operator balance: ", operator_balance)
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(system_program, is_signer=False, is_writable=True)
    ]
    for acc in additional_accounts:
        print("Additional acc ", acc)
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


def make_ExecuteTrxFromAccount(
    operator: Keypair,
    operator_balance: Pubkey,
    evm_loader_id: Pubkey,
    holder_address: Pubkey,
    treasury_address: Pubkey,
    treasury_buffer: bytes,
    additional_accounts: tp.List[Pubkey],
    additional_signers: tp.List[Keypair] = None,
    system_program=sp.ID,
    tag=0x33
):
    data = bytes([tag]) + treasury_buffer
    print("make_ExecuteTrxFromInstruction accounts")
    print("Operator: ", operator.pubkey())
    print("Treasury: ", treasury_address)
    print("Operator eth solana: ", operator_balance)
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
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
                AccountMeta(acc.pubkey(), is_signer=True, is_writable=True),
            )
    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


def make_ExecuteTrxFromAccountDataIterativeOrContinue(
    index: int,
    step_count: int,
    operator: Keypair,
    operator_balance: Pubkey,
    evm_loader_id: Pubkey,
    holder_address: Pubkey,
    treasury,
    additional_accounts: tp.List[Pubkey],
    sys_program_id=sp.ID,
    tag=0x35
):
    # 0x35 - TransactionStepFromAccount
    # 0x36 - TransactionStepFromAccountNoChainId
    data = tag.to_bytes(1, "little") + treasury.buffer + step_count.to_bytes(4, "little") + index.to_bytes(4, "little")
    print("make_ExecuteTrxFromAccountDataIterativeOrContinue accounts")
    print("Holder: ", holder_address)
    print("Operator: ", operator.pubkey())
    print("Treasury: ", treasury.account)
    print("Operator eth solana: ", operator_balance)
    accounts = [
        AccountMeta(pubkey=holder_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(sys_program_id, is_signer=False, is_writable=True)
    ]

    for acc in additional_accounts:
        print("Additional acc ", acc)
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


def make_PartialCallOrContinueFromRawEthereumTX(
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
    tag=0x34  # TransactionStepFromInstruction
):
    data = bytes([tag]) + treasury.buffer + step_count.to_bytes(4, "little") + index.to_bytes(4, "little") + instruction

    accounts = [
        AccountMeta(pubkey=storage_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator.pubkey(), is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury.account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_balance, is_signer=False, is_writable=True),
        AccountMeta(system_program, is_signer=False, is_writable=True)
    ]
    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


def make_Cancel(
    evm_loader_id: Pubkey,
    storage_address: Pubkey,
    operator: Keypair,
    operator_balance: Pubkey,
    hash_: bytes,
    additional_accounts: tp.List[Pubkey],
):
    data = bytes([0x37]) + hash_

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


def make_DepositV03(
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
    data = bytes([0x31]) + ether_address + chain_id.to_bytes(8, "little")

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


def make_CreateAssociatedTokenIdempotent(payer: Pubkey, owner: Pubkey, mint: Pubkey) -> Instruction:
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
            AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False)
        ],
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
    )


def make_CreateBalanceAccount(
    evm_loader_id: Pubkey,
    sender_pubkey: Pubkey,
    ether_address: bytes,
    account_pubkey: Pubkey,
    contract_pubkey: Pubkey,
    chain_id,
) -> Instruction:
    print("createBalanceAccount: {}".format(account_pubkey))

    data = bytes([0x30]) + ether_address + chain_id.to_bytes(8, "little")
    return Instruction(
        program_id=evm_loader_id,
        data=data,
        accounts=[
            AccountMeta(pubkey=sender_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=account_pubkey, is_signer=False, is_writable=True),
            AccountMeta(pubkey=contract_pubkey, is_signer=False, is_writable=True)
        ],
    )


def make_SyncNative(account: Pubkey):
    keys = [AccountMeta(pubkey=account, is_signer=False, is_writable=True)]
    data = bytes.fromhex("11")
    return Instruction(accounts=keys, program_id=TOKEN_PROGRAM_ID, data=data)


def make_CreateAccountWithSeed(funding, base, seed, lamports, space, program):
    created = Pubkey(sha256(bytes(base) + bytes(seed, "utf8") + bytes(program)).digest())
    print(f"Created: {created}")
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


def make_CreateHolderAccount(account, operator, seed, evm_loader_id):
    return Instruction(
        accounts=[
            AccountMeta(pubkey=account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator, is_signer=True, is_writable=False),
        ],
        program_id=evm_loader_id,
        data=bytes.fromhex("24") + len(seed).to_bytes(8, "little") + seed,
    )


def make_wSOL(amount, solana_wallet, ata_address):
    tx = Transaction(fee_payer=solana_wallet)
    tx.add(sp.transfer(sp.TransferParams(
        from_pubkey=solana_wallet, to_pubkey=ata_address, lamports=amount)
    ))
    tx.add(make_SyncNative(ata_address))

    return tx


def make_OperatorBalanceAccount(operator_keypair, operator_balance_pubkey, ether_bytes, chain_id, evm_loader_id):
    trx = Transaction()
    trx.add(Instruction(
        accounts=[
            AccountMeta(pubkey=operator_keypair.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=True),
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
