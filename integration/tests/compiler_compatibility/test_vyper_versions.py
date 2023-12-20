import pytest
import utils.vyperx as vyperx
from integration.tests.compiler_compatibility.helpers.erc_20_common_checks import (
    check_erc20_mint_function,
    check_erc20_transfer_function,
)

INIT_NAME = "SampleToken"
INIT_SYMBOL = "ST"
INIT_DECIMALS = 18
INIT_SUPPLY = 1000


class TestVyperCompatibility:
    @pytest.fixture(scope="class", autouse=True, params=vyperx.get_three_last_versions())
    def install_vyper(self, request):
        vyperx.install(request.param)
        print(f"{request.param} vyper version installed")

    @pytest.fixture
    def erc20_vyper(self, web3_client, class_account):
        return web3_client.compile_by_vyper_and_deploy(
            class_account, "Erc20", [INIT_NAME, INIT_SYMBOL, INIT_DECIMALS, INIT_SUPPLY]
        )

    @pytest.fixture
    def forwarder(self, web3_client, class_account):
        return web3_client.compile_by_vyper_and_deploy(class_account, "Forwarder")

    @pytest.fixture
    def simple(self, web3_client, class_account):
        return web3_client.compile_by_vyper_and_deploy(class_account, "Simple")

    def test_name(self, erc20_vyper):
        assert erc20_vyper.functions.name().call() == INIT_NAME

    def test_mint(self, erc20_vyper, class_account, web3_client):
        check_erc20_mint_function(web3_client, erc20_vyper, class_account)

    def test_transfer(self, erc20_vyper, class_account, new_account, web3_client):
        check_erc20_transfer_function(web3_client, erc20_vyper, class_account, new_account)

    def test_deploy_contract_by_contract(self, simple, forwarder, class_account, web3_client):
        tx = web3_client._make_tx_object(class_account.address, gas=0)
        del tx["gas"]

        instr = forwarder.functions.deploy(simple.address, class_account.address).build_transaction(tx)
        resp = web3_client.send_transaction(class_account, instr)
        assert resp["status"] == 1
