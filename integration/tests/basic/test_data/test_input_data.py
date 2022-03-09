from enum import Enum


class TestInputData(Enum):
    FIRST_FAUCET_REQUEST_AMOUNT = 5
    SECOND_FAUCET_REQUEST_AMOUNT = 3
    FIRST_AMOUNT_IN_RESPONSE = '0x4563918244f40000'
    DEFAULT_TRANSFER_AMOUNT = 3
    NEGATIVE_AMOUNT = -1
    SAMPLE_AMOUNT = 4
    ROUND_DIGITS = 3

    def get_default_amount(self) -> int:
        return self.DEFAULT_TRANSFER_AMOUNT.value

    def get_default_initial_amount(self) -> int:
        return self.FIRST_FAUCET_REQUEST_AMOUNT.value
