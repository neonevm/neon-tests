from enum import Enum

from solders.pubkey import Pubkey

OPERATOR_KEYPAIR_PATH = "deploy/operator-keypairs"
LAMPORT_PER_SOL = 1_000_000_000
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
INITIAL_ACCOUNT_AMOUNT = 100
MAX_UINT_256 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
MAX_UINT_64 = 2 ** 64

COMPUTE_BUDGET_ID: Pubkey = Pubkey.from_string("ComputeBudget111111111111111111111111111111")
MEMO_PROGRAM_ID: Pubkey = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
SOLANA_CALL_PRECOMPILED_ID: Pubkey = Pubkey.from_string("83fAnx3LLG612mHbEh4HzXEpYwvSB5fqpwUS3sZkRuUB")
COUNTER_ID: Pubkey = Pubkey.from_string("4RJAXLPq1HrXWP4zFrMhvB5drrzqrRFwaRVNUnALcaeh")
TRANSFER_SOL_ID: Pubkey = Pubkey.from_string("6x9dAYQehxXLh16EHAKXevnQADTZPKP6ZT4t8BfNDxtB")
TRANSFER_TOKENS_ID: Pubkey = Pubkey.from_string("BFsGPJUwgE1rz4eoL322HaKZYNZ5wDLafwYtKwomv2XF")
TEST_INVOKE_ID: Pubkey = Pubkey.from_string("8iqgWRzFNXmpUHLffB6uJD1ER3NLLq2ND3BioNgG9ZpZ")


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


class InputTestConstants(Enum):
    NEW_USER_REQUEST_AMOUNT = 200
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
