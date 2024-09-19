import typing as tp
import enum
from dataclasses import dataclass

from solders.pubkey import Pubkey
from solders.keypair import Keypair


@dataclass
class TreasuryPool:
    index: int
    account: Pubkey
    buffer: bytes


@dataclass
class Caller:
    solana_account: Keypair
    solana_account_address: Pubkey
    balance_account_address: Pubkey
    eth_address: bytes
    token_address: Pubkey


@dataclass
class Contract:
    eth_address: bytes
    solana_address: Pubkey
    balance_account_address: Pubkey


@dataclass
class TreasuryPool:
    index: int
    account: Pubkey
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


RepoType = tp.Literal["proxy", "evm", "tests"]
