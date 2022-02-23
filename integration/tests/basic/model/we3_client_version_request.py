from dataclasses import dataclass

from integration.tests.basic.model.rpc_request import RpcRequest


@dataclass
class Web3ClientVersion(RpcRequest):
    id: int
    result: str
