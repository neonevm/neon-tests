import typing as tp
import enum
from dataclasses import dataclass

from solana.publickey import PublicKey
from solana.keypair import Keypair


@dataclass
class TreasuryPool:
    index: int
    account: PublicKey
    buffer: bytes


@dataclass
class Caller:
    solana_account: Keypair
    solana_account_address: PublicKey
    balance_account_address: PublicKey
    eth_address: bytes
    token_address: PublicKey


@dataclass
class Contract:
    eth_address: bytes
    solana_address: PublicKey
    balance_account_address: PublicKey


@dataclass
class TreasuryPool:
    index: int
    account: PublicKey
    buffer: bytes


TestGroup = tp.Literal[
    "economy",
    "basic",
    "tracer",
    "services",
    "oz",
    "ui",
    "evm",
    "compiler_compatibility",
]


class TransactionType(enum.IntEnum):
    LEGACY = 0
    EIP_1559 = 2
