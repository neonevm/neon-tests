from enum import Enum


class InputData(Enum):
    FAUCET_1ST_REQUEST_AMOUNT = 5
    FAUCET_2ND_REQUEST_AMOUNT = 3
    FIRST_AMOUNT_IN_RESPONSE = '0x4563918244f40000'
    DEFAULT_TRANSFER_AMOUNT = 0.01
    NEGATIVE_AMOUNT = -0.1
    SAMPLE_AMOUNT = 0.02
    ROUND_DIGITS = 3

    def get_transfer_amount(self) -> int:
        return self.DEFAULT_TRANSFER_AMOUNT.value

    def get_default_initial_amount(self) -> int:
        return self.FAUCET_1ST_REQUEST_AMOUNT.value
