from typing import List, Optional

from pydantic import BaseModel, field_validator

from integration.tests.basic.helpers.errors import Error32602
from utils.models.mixins import ForbidExtra
from utils.models.model_types import (
    ErrorCodeField,
    IdField,
    JsonRPCString,
    NotSupportedMethodString,
    RequiredParamsString,
)


class EthErrorData(ForbidExtra):
    errors: List[str]

    @field_validator("errors")
    def check_errors_list(cls, value):
        if len(value) == 0:
            raise ValueError("errors must be in a list")


class EthErrorDetail(ForbidExtra):
    code: int
    message: str
    data: Optional[EthErrorData] = None

    @field_validator("message")
    def check_message(cls, value):
        if not isinstance(value, str):
            raise ValueError("message must be a string")
        if len(value) == 0:
            raise ValueError("message must be non-empty")

    @field_validator("code")
    def check_code(cls, value):
        if not isinstance(value, int):
            raise ValueError("code must be an integer")
        if value > 0:
            raise ValueError("code must be negative")


class EthErrorDetailNotSupportedMethod(BaseModel):
    code: ErrorCodeField
    message: NotSupportedMethodString


class EthError(ForbidExtra):
    jsonrpc: JsonRPCString
    id: IdField
    error: EthErrorDetail


class EthError32602(EthError):
    message: str = Error32602.INVALID_ADDRESS


class MissingValueDetail(ForbidExtra):
    code: int = -32602
    message: str = "missing value for required argument 0"


class MissingValueError(EthError):
    error: MissingValueDetail


class NotSupportedMethodError(EthError):
    error: EthErrorDetailNotSupportedMethod


class FieldRequiredData(ForbidExtra):
    errors: List[RequiredParamsString]


class FieldRequiredDetail(ForbidExtra):
    code: int = -32602
    message: str = Error32602.INVALID_PARAMETERS
    data: FieldRequiredData


class FieldRequiredError(EthError):
    error: FieldRequiredDetail
