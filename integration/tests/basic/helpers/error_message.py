from enum import Enum


class ErrorMessage(Enum):
    NEGATIVE_VALUE = "Resulting wei value must be between 1 and 2**256 - 1"
    EXPECTING_VALUE = "Expecting value: line 1 column 1 (char 0)"
