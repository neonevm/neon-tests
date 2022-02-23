from dataclasses import dataclass

from integration.tests.basic.model.rpc_request import RpcRequest


@dataclass
class GetBlockByHashRequest(RpcRequest):
    params: str # TODO
    method: str = "eth_getBlockByHash"
