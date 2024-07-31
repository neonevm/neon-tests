import typing as tp
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

GithubEvent = tp.Literal[
    "push_no_tag",
    "push_with_tag",
    "pull_request",
    "merge_request",
    "workflow_dispatch",
    "unknown",
]

RepoType = tp.Literal["proxy", "evm", "tests"]
