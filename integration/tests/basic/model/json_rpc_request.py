from dataclasses import dataclass
# from typing import List

from integration.tests.basic.model.json_rpc_request_parameters import JsonRpcRequestParams


@dataclass
class JsonRpcRequest():
    id: int
    method: str
    params: JsonRpcRequestParams
    jsonrpc: str = "2.0"
