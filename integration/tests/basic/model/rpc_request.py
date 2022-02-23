from dataclasses import dataclass


@dataclass
class RpcRequest():
    id: int
    method: str
    params: str  # TODO
    jsonrpc: str = "2.0"
