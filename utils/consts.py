from enum import Enum

from solana.publickey import PublicKey

LAMPORT_PER_SOL = 1_000_000_000
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_HASH = "0000000000000000000000000000000000000000000000000000000000000000"
INITIAL_ACCOUNT_AMOUNT = 100
MAX_UINT_256 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF


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
    NEW_USER_REQUEST_AMOUNT = 100
    DEFAULT_TRANSFER_AMOUNT = 0.1
    SAMPLE_AMOUNT = 0.5
    ROUND_DIGITS = 3


wSOL = {
    "chain_id": 111,
    "address_spl": PublicKey("So11111111111111111111111111111111111111112"),
    "address": "0x16869acc45BA20abEFB2DdE2096F66373fDe364F",
    "decimals": 9,
    "name": "Wrapped SOL",
    "symbol": "wSOL",
    "logo_uri": "https://raw.githubusercontent.com/neonlabsorg/token-list/master/assets/solana-wsol-logo.svg",
}
