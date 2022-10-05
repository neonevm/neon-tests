# coding: utf-8
"""
Created on 2022-08-29
@author: Eugeny Kurkovich
"""
import typing as tp
from dataclasses import dataclass
from hashlib import sha256

from construct import Bytes, Int8ul, Struct, Int32ul
from eth_keys import keys as eth_keys
from solana.publickey import PublicKey
from solana.rpc import commitment
from solana.transaction import Transaction, TransactionInstruction

ACCOUNT_INFO_LAYOUT = Struct(
    "type" / Int8ul,
    "ether" / Bytes(20),
    "nonce" / Int8ul,
    "tx_count" / Bytes(8),
    "balance" / Bytes(32),
    "generation" / Int32ul,
    "code_size" / Int32ul,
    "is_rw_blocked" / Int8ul,
)


DEFAULT_UNITS = 500 * 1000
DEFAULT_HEAP_FRAME = 256 * 1024
DEFAULT_ADDITIONAL_FEE = 0
COMPUTE_BUDGET_ID: PublicKey = PublicKey("ComputeBudget111111111111111111111111111111")
SYSTEM_ADDRESS = "11111111111111111111111111111111"


@dataclass
class AccountInfo:
    ether: eth_keys.PublicKey
    trx_count: int

    @staticmethod
    def from_bytes(data: bytes):
        cont = ACCOUNT_INFO_LAYOUT.parse(data)
        return AccountInfo(cont.ether, cont.tx_count)


@dataclass
class SOLCommitmentState:
    """Bank states to solana query"""

    CONFIRMED: str = commitment.Confirmed
    FINALIZED: str = commitment.Finalized
    PROCESSED: str = commitment.Processed


@dataclass
class TreasuryPoolBases:
    """Collateral pool base address"""

    DEVNET: str = "7SBdHNeF9FFYySEoszpjZXXQsAiwa5Lzpsz6nUJWusEx"
    NIGHT_STAND: str = "4sW3SZDJB7qXUyCYKA7pFL8eCTfm3REr8oSiKkww7MaT"

    @classmethod
    def get_by_network(cls, network: str) -> str:
        """Get collateral pool base address"""
        return getattr(cls, network.replace("-", "_").upper(), cls.NIGHT_STAND)


@dataclass
class TreasuryPool:
    index: int
    account: PublicKey
    buffer: bytes


class ComputeBudget:
    @staticmethod
    def request_units(units, additional_fee):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[],
            data=bytes.fromhex("00") + units.to_bytes(4, "little") + additional_fee.to_bytes(4, "little"),
        )

    @staticmethod
    def request_heap_frame(heap_frame):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID, keys=[], data=bytes.fromhex("01") + heap_frame.to_bytes(4, "little")
        )


class TransactionWithComputeBudget(Transaction):
    def __init__(
        self, units=DEFAULT_UNITS, additional_fee=DEFAULT_ADDITIONAL_FEE, heap_frame=DEFAULT_HEAP_FRAME, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        if units:
            self.instructions.append(ComputeBudget.request_units(units, additional_fee))
        if heap_frame:
            self.instructions.append(ComputeBudget.request_heap_frame(heap_frame))


def gen_account_with_seed(base, seed, program) -> PublicKey:
    return PublicKey(sha256(bytes(base) + bytes(seed, "utf8") + bytes(program)).digest())


def create_treasury_pool_address(
    network: str, loader_id: str, collateral_pool_index: tp.Optional[int] = 2
) -> TreasuryPool:
    """Create treasury pool address"""
    collateral_seed_prefix = "collateral_seed_"
    seed = collateral_seed_prefix + str(collateral_pool_index)
    address = gen_account_with_seed(PublicKey(TreasuryPoolBases.get_by_network(network)), seed, PublicKey(loader_id))
    index_buf = collateral_pool_index.to_bytes(4, "little")
    return TreasuryPool(collateral_pool_index, address, index_buf)
