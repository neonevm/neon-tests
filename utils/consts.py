from pathlib import Path
import typing as tp

from enum import Enum
from utils.types import TestGroup
from solders.pubkey import Pubkey


EXTERNAL_CONTRACT_PATH = Path.cwd() / "contracts" / "external"
REMAPPING_ZEPPELIN = {"@openzeppelin": str(EXTERNAL_CONTRACT_PATH / "neon-contracts/node_modules/@openzeppelin")}
TEST_GROUPS: tp.Tuple[TestGroup, ...] = tp.get_args(TestGroup)

OPERATOR_KEYPAIR_PATH = "deploy/operator-keypairs"
LAMPORT_PER_SOL = 1_000_000_000
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
INITIAL_ACCOUNT_AMOUNT = 100
MAX_UINT_256 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
MAX_UINT_64 = 2**64

COMPUTE_BUDGET_ID: Pubkey = Pubkey.from_string("ComputeBudget111111111111111111111111111111")
MEMO_PROGRAM_ID: Pubkey = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
SOLANA_CALL_PRECOMPILED_ID: Pubkey = Pubkey.from_string("83fAnx3LLG612mHbEh4HzXEpYwvSB5fqpwUS3sZkRuUB")
COUNTER_ID: Pubkey = Pubkey.from_string("FUVnLFCgK48arAUgngmyYkSSKKD2PpjsneNTyigbe4oh")
TRANSFER_SOL_ID: Pubkey = Pubkey.from_string("6x9dAYQehxXLh16EHAKXevnQADTZPKP6ZT4t8BfNDxtB")
TRANSFER_TOKENS_ID: Pubkey = Pubkey.from_string("BFsGPJUwgE1rz4eoL322HaKZYNZ5wDLafwYtKwomv2XF")
TEST_INVOKE_ID: Pubkey = Pubkey.from_string("2Uax3YiG6wiAcCdDCAZwKSuzi47w3cidMRQQnteMJJCT")
QUERY_ACCOUNT_ID: Pubkey = Pubkey.from_string("Fbc3Hf6FK7wCQjQHq9qS2phvhujfkfMQQWLsyA5s4oSu")

SPL_TOKEN_ADDRESS = "0xFf00000000000000000000000000000000000004"
METAPLEX_ADDRESS = "0xff00000000000000000000000000000000000005"
CALL_SOLANA_ADDRESS = "0xFF00000000000000000000000000000000000006"
SOLANA_NATIVE_ADDRESS = "0xfF00000000000000000000000000000000000007"


class Time:
    MINUTE = 60
    HOUR = 60 * MINUTE
    DAY = 24 * HOUR
    WEEK = 7 * DAY
    MONTH = 30 * DAY
    YEAR = 365 * DAY


class Unit(Enum):
    WEI = "wei"
    KWEI = "kwei"
    MWEI = "mwei"
    GWEI = "gwei"
    MICRO_ETHER = "microether"
    MILLI_ETHER = "milliether"
    ETHER = "ether"

    def lower(self):
        return self.value


class EnvName(str, Enum):
    NIGHT_STAND = "night-stand"
    RELEASE_STAND = "release-stand"
    MAINNET = "mainnet"
    DEVNET = "devnet"
    TESTNET = "testnet"
    LOCAL = "local"
    TERRAFORM = "terraform"
    GETH = "geth"
    TRACER_CI = "tracer_ci"
    CUSTOM = "custom"
    DOCKER_NET = "docker_net"


class InputTestConstants(Enum):
    NEW_USER_REQUEST_AMOUNT = 20000
    DEFAULT_TRANSFER_AMOUNT = 0.1
    SAMPLE_AMOUNT = 0.5
    ROUND_DIGITS = 3


wSOL = {
    "chain_id": 111,
    "address_spl": Pubkey.from_string("So11111111111111111111111111111111111111112"),
    "address": "0x16869acc45BA20abEFB2DdE2096F66373fDe364F",
    "decimals": 9,
    "name": "Wrapped SOL",
    "symbol": "wSOL",
    "logo_uri": "",
}

MULTITOKEN_MINTS = {
    "USDT": "2duuuuhNJHUYqcnZ7LKfeufeeTBgSJdftf2zM3cZV6ym",
    "ETH": "EwJYd3UAFAgzodVeHprB2gMQ68r4ZEbbvpoVzCZ1dGq5",
}


class InstructionTags(bytes, Enum):
    HOLDER_CREATE = b"\x24"
    HOLDER_DELETE = b"\x25"
    HOLDER_WRITE = b"\x26"
    CREATE_MAIN_TREASURY = b"\x29"
    ACCOUNT_CREATE_BALANCE = b"\x30"
    DEPOSIT = b"\x31"
    TRANSACTION_EXECUTE_FROM_INSTRUCTION = b"\x3D"
    TRANSACTION_EXECUTE_FROM_ACCOUNT = b"\x33"
    TRANSACTION_STEP_FROM_INSTRUCTION = b"\x34"
    TRANSACTION_STEP_FROM_ACCOUNT = b"\x35"
    TRANSACTION_STEP_FROM_ACCOUNT_NO_CHAIN_ID = b"\x36"
    CANCEL = b"\x37"
    TRANSACTION_EXECUTE_FROM_INSTRUCTION_WITH_SOLANA_CALL = b"\x3E"
    TRANSACTION_EXECUTE_FROM_ACCOUNT_WITH_SOLANA_CALL = b"\x39"
    OPERATOR_BALANCE_CREATE = b"\x3A"
    OPERATOR_BALANCE_DELETE = b"\x3B"
    OPERATOR_BALANCE_WITHDRAW = b"\x3C"
    SCHEDULED_TRANSACTION_START_FROM_ACCOUNT = b"\x46"
    SCHEDULED_TRANSACTION_START_FROM_INSTRUCTION = b"\x47"
    SCHEDULED_TRANSACTION_SKIP_FROM_INSTRUCTION = b"\x4E"
    SCHEDULED_TRANSACTION_SKIP_FROM_ACCOUNT = b"\x4D"
    SCHEDULED_TRANSACTION_FINISH = b"\x49"
    SCHEDULED_TRANSACTION_CREATE = b"\x4A"
    SCHEDULED_TRANSACTION_CREATE_MULTIPLE = b"\x4B"
    SCHEDULED_TRANSACTION_DESTROY = b"\x4C"
    SET_COMPUTE_UNIT_PRICE = b"\x03"
    SET_COMPUTE_UNIT_LIMIT = b"\x02"
