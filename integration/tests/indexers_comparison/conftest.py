import pytest

from integration.tests.indexers_comparison.constants import ENVS
from utils.apiclient import JsonRPCSession
from utils.web3client import NeonChainWeb3Client


@pytest.fixture
def endpoints():
    clients = []
    for env in ENVS:
        clients.append(
            {
                "name": env["name"],
                "web3_client": NeonChainWeb3Client(env["url"]),
                "rpc_client": JsonRPCSession(env["url"]),
            }
        )
    return clients
