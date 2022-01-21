import web3
import solana.rpc.api
import pytest

from utils.operator import Operator
from utils.faucet import Faucet


class BaseTests:
    operator: Operator
    faucet: Faucet
    web3_client: web3.Web3
    sol_client: solana.rpc.api.Client

    @pytest.fixture(autouse=True)
    def prepare(self, operator: Operator, faucet: Faucet, web3_client, sol_client):
        self.operator = operator
        self.faucet = faucet
        self.web3_client = web3_client
        self.sol_client = sol_client
