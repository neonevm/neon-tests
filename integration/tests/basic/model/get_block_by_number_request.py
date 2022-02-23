from dataclasses import dataclass

from integration.tests.basic.model.rpc_request import RpcRequest


@dataclass
class GetBlockByNumberRequest(RpcRequest):
    id: int
    params: str  # TODO
    method: "eth_getBlockByNumber"
