from dataclasses import dataclass

from integration.tests.basic.model.rpc_request_parameters import RpcRequestParams


@dataclass
class RpcRequest():
    id: int
    method: str
    params: RpcRequestParams
    jsonrpc: str = "2.0"
