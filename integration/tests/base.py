import pytest

import eth_account.signers.local

from utils.consts import Unit
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

    def create_tx_object(self, sender, recipient=None, value=None, amount=0, nonce=None, gas=None, gas_price=None, data=None,
                         estimate_gas=True):
        if gas_price is None:
            gas_price = self.web3_client.gas_price()

        if nonce is None:
            nonce = self.web3_client.eth.get_transaction_count(sender)
        transaction = {
            "from": sender,
            "chainId": self.web3_client._chain_id,
            "gasPrice": gas_price,
            "nonce": nonce,
        }
        if gas is not None:
            transaction["gas"] = gas
            
        if value is not None:
            transaction["value"] = value
        else:
            transaction["value"] = self.web3_client.to_wei(amount, Unit.ETHER)

        if recipient is not None:
            transaction["to"] = recipient

        if data is not None:
            transaction["data"] = data

        if estimate_gas:
            transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        return transaction
