from enum import Enum


class AssertMessage(Enum):
    WRONG_ID = "Id of the response does not correspond to id of the request"
    WRONG_TYPE = "The response type is error response"
    DOES_NOT_START_WITH_0X = "Result does not start with 0x"
    WRONG_AMOUNT = "Wrong amount returned"
    CONTAINS_ERROR = "Contains the error data"
    DOES_NOT_CONTAIN_RESULT = "Does not contain the result data"
    IVALID_ARG_1_GIVEN = "takes 0 positional arguments but 1 was given"
    IVALID_ARG_2_GIVEN = "takes 1 positional argument but 2 were given"
    NOT_HEX_STR = "data is not hex string"
    MISS_1_REQ_ARG = "missing 1 required positional argument"
