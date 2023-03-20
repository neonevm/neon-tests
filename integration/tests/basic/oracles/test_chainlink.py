import math
import allure
import pytest
import requests

from integration.tests.base import BaseTests


SOL_USD_ID = "0x78f57ae1195e8c497a8be054ad52adf4c8976f8436732309e22af7067724ad96"
CHAINLINK_URI = "https://min-api.cryptocompare.com/"


@allure.story("Oracles: Verify Chainlink Network")
class TestChainlink(BaseTests):
    @pytest.mark.only_devnet
    def test_deploy_contract_chainlink_network(self):
        """Deploy chainlink contract, then get the latest price for SOL/USD"""
        contract, _ = self.web3_client.deploy_and_get_contract(
            contract="./chainlink/ChainlinkOracle",
            version="0.8.15",
            account=self.acc,
            constructor_args=[SOL_USD_ID],
        )
        version = contract.functions.version().call()
        description = contract.functions.description().call()
        decimals = contract.functions.decimals().call()
        latest_round_data = contract.functions.latestRoundData().call()

        assert version == 2
        assert description == "SOL / USD"
        assert decimals == 8

        latest_price = latest_price_feeds("SOL", "USD")
        assert math.isclose(
            abs(latest_price - latest_round_data[1] * 1e-8), 0.0, rel_tol=1
        )

    @pytest.mark.only_devnet
    def test_deploy_contract_chainlink_network_get_price(self):
        """Call latest price for SOL/USD from another contract"""
        _, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            contract="./chainlink/ChainlinkOracle",
            version="0.8.15",
            account=self.acc,
            constructor_args=[SOL_USD_ID],
        )
        contract, _ = self.web3_client.deploy_and_get_contract(
            contract="./chainlink/GetLatestData", version="0.8.15", account=self.acc
        )

        address = contract_deploy_tx["contractAddress"]
        version = contract.functions.getVersion(address).call()
        description = contract.functions.getDescription(address).call()
        decimals = contract.functions.getDecimals(address).call()
        latest_data = contract.functions.getLatestData(address).call()

        assert version == 2
        assert description == "SOL / USD"
        assert decimals == 8

        latest_price = latest_price_feeds("SOL", "USD")
        assert math.isclose(abs(latest_price - latest_data[1] * 1e-8), 0.0, rel_tol=1)


def latest_price_feeds(sym_one, sym_two):
    response = requests.get(
        CHAINLINK_URI + f"data/pricemultifull?fsyms={sym_one}&tsyms={sym_two}"
    )
    return response.json()["RAW"][f"{sym_one}"][f"{sym_two}"]["PRICE"]
