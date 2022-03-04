from enum import Enum


class AssertMessage(Enum):
    WRONG_ID = "Id of the response does not correspond to id of the request"
    WRONG_TYPE = "The response type is error response"
    DOES_NOT_START_WITH_0X = "result does not start with 0x"
    WRONG_AMOUNT = "Wrong amount returned"
