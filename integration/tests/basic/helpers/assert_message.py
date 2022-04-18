from enum import Enum

from integration.tests.basic.helpers.error_message import ErrorMessage


class AssertMessage(Enum):
    WRONG_ID = "Id of the response does not correspond to id of the request"
    WRONG_TYPE = "The response type is error response"
    DOES_NOT_START_WITH_0X = "Result does not start with 0x"
    WRONG_AMOUNT = "Wrong amount returned"
    CONTAINS_ERROR = "Contains the error data"
    DOES_NOT_CONTAIN_RESULT = "Does not contain the result data"
    DOES_NOT_CONTAIN_TOO_LOW = f"Message does not contain '{ErrorMessage.NONCE_TOO_LOW.value}'"
    DOES_NOT_CONTAIN_TOO_HIGH = f"Message does not contain '{ErrorMessage.NONCE_TOO_HIGH.value}'"
