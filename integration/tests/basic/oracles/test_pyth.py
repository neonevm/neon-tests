import math
import allure
import pytest
import requests

from integration.tests.base import BaseTests


BTC_USD_ID = "0xf9c0172ba10dfa4d19088d94f5bf61d3b54d5bd7483a322a982e1373ee8ea31b"
PYTH_DEVNET_URI = "https://xc-testnet.pyth.network"


@allure.feature("Oracles")
@allure.story("Pyth network")
class TestPyth(BaseTests):
    @pytest.mark.only_devnet
    def test_deploy_contract_pyth_network(self):
        """Deploy pyth contract, then get current price for BTC/USD"""
        contract, _ = self.web3_client.deploy_and_get_contract(
            "./pyth/PythOracle", "0.8.0", account=self.acc
        )

        price = contract.functions.getCurrentPrice(BTC_USD_ID).call()

        latest_price, conf, expo = latest_price_feeds(BTC_USD_ID)
        assert math.isclose(
            abs(latest_price - int(price[0])), 0.0, rel_tol=conf * (10 ** expo)
        )

    @pytest.mark.only_devnet
    def test_deploy_contract_pyth_network_get_price(self):
        """Call current price for BTC/USD from another contract"""
        _, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "./pyth/PythOracle", "0.8.0", account=self.acc
        )
        contract, _ = self.web3_client.deploy_and_get_contract(
            "./pyth/GetPrice", "0.8.0", account=self.acc
        )

        address = contract_deploy_tx["contractAddress"]
        price = contract.functions.get(address, BTC_USD_ID).call()

        latest_price, conf, expo = latest_price_feeds(BTC_USD_ID)
        assert math.isclose(abs(latest_price - price), 0.0, rel_tol=conf * (10 ** expo))


def latest_price_feeds(feed_id):
    response = requests.get(
        PYTH_DEVNET_URI + "/api/latest_price_feeds?ids[]=" + feed_id
    )
    result = response.json()[0]["price"]
    return int(result["price"]), int(result["conf"]), int(result["expo"])
