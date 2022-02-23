from dataclasses import dataclass

from integration.tests.basic.model.rpc_request import RpcRequest


@dataclass
class EstimateGasRequest(RpcRequest):
    id: int
    params: str  # {"jsonrpc":"2.0","method":"eth_estimateGas","params":[{see above}],"id":1}'
    method: "eth_estimateGas"
