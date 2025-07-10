import typing as tp
from enum import Enum
from pathlib import Path

from solders.pubkey import Pubkey

from utils.types import TestGroup

EXTERNAL_CONTRACT_PATH = Path.cwd() / "contracts" / "external"
REMAPPING_ZEPPELIN = {"@openzeppelin": str(EXTERNAL_CONTRACT_PATH / "neon-contracts/node_modules/@openzeppelin")}
REMAPPING_ZEPPELIN_UNISWAP = {
    "@openzeppelin": str(EXTERNAL_CONTRACT_PATH / "uniswap-v3/node_modules/@openzeppelin"),
    "base64-sol": str(EXTERNAL_CONTRACT_PATH / "uniswap-v3/node_modules/base64-sol"),
    "@uniswap": str(EXTERNAL_CONTRACT_PATH / "uniswap-v3/node_modules/@uniswap"),
}
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
TEST_INVOKE_ID: Pubkey = Pubkey.from_string("A4HqdWTdJku9MB4FZfzv5YjsPmGCxX8NfKcrQJh2spqu")
QUERY_ACCOUNT_ID: Pubkey = Pubkey.from_string("Fbc3Hf6FK7wCQjQHq9qS2phvhujfkfMQQWLsyA5s4oSu")
ALT_UPDATER_ID: Pubkey = Pubkey.from_string("2opr1VoyXxpNePA4gcLBGPMPgrzgpyixuqDrE7EzKFWv")

SPL_TOKEN_ADDRESS = "0xFf00000000000000000000000000000000000004"
METAPLEX_ADDRESS = "0xff00000000000000000000000000000000000005"
CALL_SOLANA_ADDRESS = "0xFF00000000000000000000000000000000000006"
SOLANA_NATIVE_ADDRESS = "0xfF00000000000000000000000000000000000007"

PAYMENT_FOR_TREE_ACCOUNT_DELETING = 10_000  # Paid by neon_user for tree_acc deleting. Do not depend on trx_count
TRX_EXECUTION_PRICE = 5_000  # Standard fee for trx execution in solana. Paid by neon_user fox tree_acc creation
LAMPORT_TO_INNER_SOL = 10**9  # Exchange coefficient from outer sol to inner sol
OPERATOR_FEE_TO_NEON = 5_000  # Paid by operator to treasury account per iteration. Fee for trx execution inside Neon
TREE_ACCOUNT_BALANCE_STRUCT_ENLARGEMENT_COST = (
    222_720  # Cost of enlarging balance account struct during tree_acc creation +32 bytes
)


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


MULTITOKEN_MINTS_USDT = "2duuuuhNJHUYqcnZ7LKfeufeeTBgSJdftf2zM3cZV6ym"


class InstructionTags(bytes, Enum):
    COLLECT_TREASURE = b"\x1e"
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
    SCHEDULED_TRANSACTION_FINISH = b"\x49"
    SCHEDULED_TRANSACTION_CREATE = b"\x4A"
    SCHEDULED_TRANSACTION_CREATE_MULTIPLE = b"\x4B"
    SCHEDULED_TRANSACTION_DESTROY = b"\x4C"
    SCHEDULED_TRANSACTION_SKIP_FROM_ACCOUNT = b"\x4D"
    SCHEDULED_TRANSACTION_SKIP_FROM_INSTRUCTION = b"\x4E"
    SET_COMPUTE_UNIT_PRICE = b"\x03"
    SET_COMPUTE_UNIT_LIMIT = b"\x02"
    CONFIG_GET_CHAIN_COUNT = b"\xA0"
    CONFIG_GET_CHAIN_INFO = b"\xA1"
    CONFIG_GET_ENVIRONMENT = b"\xA2"
    CONFIG_GET_PROPERTY_COUNT = b"\xA3"
    CONFIG_GET_PROPERTY_BY_INDEX = b"\xA4"
    CONFIG_GET_PROPERTY_BY_NAME = b"\xA5"
    CONFIG_GET_STATUS = b"\xA6"
    CONFIG_GET_VERSION = b"\xA7"


class NeonTxExitStatus(str, Enum):
    SUCCESS_WITH_CHANGES = "0x11"
    SUCCESS_NO_CHANGES = "0x12"
    REVERT = "0xD0"
