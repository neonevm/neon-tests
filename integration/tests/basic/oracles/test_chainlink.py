import math
import pathlib

import allure
import pytest
import requests

from clickfile import EXTERNAL_CONTRACT_PATH
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts


SOL_USD_ID = "0x78f57ae1195e8c497a8be054ad52adf4c8976f8436732309e22af7067724ad96"
CHAINLINK_URI = "https://min-api.cryptocompare.com/"


@allure.feature("Oracles")
@allure.story("Chainlink")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestChainlink:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.only_devnet
    def test_deploy_contract_chainlink_network(self):
        sender_account = self.accounts[0]
        """Deploy chainlink contract, then get the latest price for SOL/USD"""
        remapping = {
            "@chainlink": str(EXTERNAL_CONTRACT_PATH / "hoodies_chainlink/node_modules/@chainlink"),
            "solidity-bytes-utils": str(EXTERNAL_CONTRACT_PATH / "hoodies_chainlink/node_modules/solidity-bytes-utils"),
        }
        utils_lib, _ = self.web3_client.deploy_and_get_contract(
            contract="./external/hoodies_chainlink/contracts/libraries/Utils.sol",
            version="0.8.19",
            account=sender_account,
            import_remapping=remapping,
        )
        contract, _ = self.web3_client.deploy_and_get_contract(
            contract="./external/hoodies_chainlink/contracts/ChainlinkOracle",
            version="0.8.19",
            account=sender_account,
            constructor_args=[SOL_USD_ID],
            import_remapping=remapping,
            libraries={"contracts/external/hoodies_chainlink/contracts/libraries/Utils.sol:Utils": utils_lib.address},
        )
        version = contract.functions.version().call()
        description = contract.functions.description().call()
        decimals = contract.functions.decimals().call()
        latest_round_data = contract.functions.latestRoundData().call()

        assert version == 2
        assert description == "SOL / USD"
        assert decimals == 8

        latest_price = latest_price_feeds("SOL", "USD")
        assert math.isclose(abs(latest_price - latest_round_data[1] * 1e-8), 0.0, rel_tol=1)


def latest_price_feeds(sym_one, sym_two):
    response = requests.get(CHAINLINK_URI + f"data/pricemultifull?fsyms={sym_one}&tsyms={sym_two}")
    return response.json()["RAW"][f"{sym_one}"][f"{sym_two}"]["PRICE"]
