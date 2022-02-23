from dataclasses import dataclass

from integration.tests.basic.model.rpc_request import RpcRequest


@dataclass
class EthBlockNumberRequest(RpcRequest):
    id: int
    params: str  # ,"params":[],"id":83}'
    method: "eth_blockNumber"
