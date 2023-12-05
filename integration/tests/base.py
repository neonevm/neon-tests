import pytest

import eth_account.signers.local

from utils.consts import Unit
from utils.faucet import Faucet
from utils.operator import Operator
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client, Web3Client


class BaseTests:
    acc: eth_account.signers.local.LocalAccount
    operator: Operator
    faucet: Faucet
    web3_client: NeonChainWeb3Client
    web3_client_sol: Web3Client
    sol_client: SolanaClient
    sol_price: float

    @pytest.fixture(autouse=True)
    def prepare(self, operator: Operator, faucet: Faucet, web3_client, web3_client_sol, sol_client):
        self.operator = operator
        self.faucet = faucet
        self.web3_client = web3_client
        self.web3_client_sol = web3_client_sol
        self.sol_client = sol_client

    @pytest.fixture(autouse=True)
    def prepare_account(self, prepare_account):
        self.acc = prepare_account

    def create_tx_object(self, sender, recipient=None, amount=0, nonce=None, gas=None, gas_price=None, data=None,
                             estimate_gas=True, web3_client=None):
        if web3_client is None:
            web3_client = self.web3_client
        if gas_price is None:
            gas_price = web3_client.gas_price()

        if nonce is None:
            nonce = web3_client.eth.get_transaction_count(sender)
        transaction = {
            "from": sender,
            "gasPrice": gas_price,
            "chainId": web3_client.eth.chain_id,
            "nonce": nonce
        }
        if gas is not None:
            transaction["gas"] = gas

        if amount is not None:
           transaction["value"] = web3_client.to_atomic_currency(amount)

        if recipient is not None:
            transaction["to"] = recipient

        if data is not None:
            transaction["data"] = data

        if estimate_gas:
            transaction["gas"] = web3_client.eth.estimate_gas(transaction)

        return transaction
