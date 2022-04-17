from enum import Enum


class ErrorMessage(Enum):
    NEGATIVE_VALUE = "Resulting wei value must be between 1 and 2**256 - 1"
    INSUFFICIENT_FUNDS = "insufficient funds for transfer"
    GAS_LIMIT_REACHED = "gas limit reached"
    INVALID_FIELDS_GAS = "Transaction had invalid fields: {'gas'"
    NONCE_TOO_LOW = "nonce too low"
    NONCE_TOO_HIGH = "nonce too high"
