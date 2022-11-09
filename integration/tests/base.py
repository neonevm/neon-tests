import pytest

import eth_account.signers.local
from utils.faucet import Faucet
from utils.operator import Operator
from utils.solana_client import SolanaClient
from utils.web3client import NeonWeb3Client


class BaseTests:
    acc: eth_account.signers.local.LocalAccount
    operator: Operator
    faucet: Faucet
    web3_client: NeonWeb3Client
    sol_client: SolanaClient
    sol_price: float

    @pytest.fixture(autouse=True)
    def prepare(self, operator: Operator, faucet: Faucet, web3_client, sol_client):
        self.operator = operator
        self.faucet = faucet
        self.web3_client = web3_client
        self.sol_client = sol_client

    @pytest.fixture(autouse=True)
    def prepare_account(self, prepare_account):
        self.acc = prepare_account
