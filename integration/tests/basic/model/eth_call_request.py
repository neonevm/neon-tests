from dataclasses import dataclass

from integration.tests.basic.model.rpc_request import RpcRequest


@dataclass
class EthCallRequest(RpcRequest):
    id: int
    params: str  # {"jsonrpc":"2.0","method":"eth_call","params":[{see above}],"id":1}'
    method: "eth_call"