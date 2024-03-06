import math
import allure
import pytest
import requests

from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.prices import get_btc_price_detailed


BTC_USD_ID = "0xf9c0172ba10dfa4d19088d94f5bf61d3b54d5bd7483a322a982e1373ee8ea31b"
PYTH_DEVNET_URI = "https://xc-testnet.pyth.network"


@allure.feature("Oracles")
@allure.story("Pyth network")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestPyth:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.only_devnet
    def test_deploy_contract_pyth_network(self):
        """Deploy pyth contract, then get current price for BTC/USD"""
        sender_account = self.accounts[0]
        contract, _ = self.web3_client.deploy_and_get_contract("./pyth/PythOracle", "0.8.0", account=sender_account)

        price = contract.functions.getCurrentPrice(BTC_USD_ID).call()

        latest_price = get_btc_price_detailed().aggregate_price
        assert math.isclose(latest_price, int(price[0]), rel_tol=10)

    @pytest.mark.only_devnet
    def test_deploy_contract_pyth_network_get_price(self):
        """Call current price for BTC/USD from another contract"""
        sender_account = self.accounts[0]
        _, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "./pyth/PythOracle", "0.8.0", account=sender_account
        )
        contract, _ = self.web3_client.deploy_and_get_contract("./pyth/GetPrice", "0.8.0", account=sender_account)

        address = contract_deploy_tx["contractAddress"]
        price = contract.functions.get(address, BTC_USD_ID).call()

        latest_price = get_btc_price_detailed().aggregate_price
        assert math.isclose(latest_price, price, rel_tol=10)
