from enum import Enum


class ErrorMessage(Enum):
    NEGATIVE_VALUE = "Resulting wei value must be between 1 and 2**256 - 1"
    EXPECTING_VALUE = "insufficient funds for transfer"
