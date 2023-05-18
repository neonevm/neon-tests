from enum import Enum


LAMPORT_PER_SOL = 1_000_000_000
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
ZERO_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

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
    FAUCET_1ST_REQUEST_AMOUNT = 2_000
    FAUCET_2ND_REQUEST_AMOUNT = 3
    DEFAULT_TRANSFER_AMOUNT = 0.1
    NEGATIVE_AMOUNT = -0.1
    SAMPLE_AMOUNT = 0.5
    ROUND_DIGITS = 3

    def get_transfer_amount(self) -> float:
        return self.DEFAULT_TRANSFER_AMOUNT.value

    def get_default_initial_amount(self) -> int:
        return self.FAUCET_1ST_REQUEST_AMOUNT.value
