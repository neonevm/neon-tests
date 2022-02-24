from dataclasses import dataclass


@dataclass
class JsonRpcErrorResponse:
    id: int
    error: object
    jsonrpc: str = "2.0"