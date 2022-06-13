import typing as tp
from dataclasses import dataclass


@dataclass
class JsonRpcRequestParams(tp.List):
    pass


@dataclass
class JsonRpcRequest:
    id: int
    method: str
    params: JsonRpcRequestParams
    jsonrpc: str = "2.0"


@dataclass
class JsonRpcResponse:
    id: int
    result: object
    jsonrpc: str = "2.0"


@dataclass
class JsonRpcErrorResponse:
    id: int
    error: object
    jsonrpc: str = "2.0"
