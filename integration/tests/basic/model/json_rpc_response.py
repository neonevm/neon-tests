from dataclasses import dataclass


@dataclass
class JsonRpcResponse:
    id: int
    result: object
    error: object
    jsonrpc: str = "2.0"
