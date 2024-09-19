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
    def erc20_vyper(self, web3_client, accounts):
        return web3_client.compile_by_vyper_and_deploy(
            accounts[0], "Erc20", [INIT_NAME, INIT_SYMBOL, INIT_DECIMALS, INIT_SUPPLY]
        )

    @pytest.fixture
    def forwarder(self, web3_client, accounts):
        return web3_client.compile_by_vyper_and_deploy(accounts[0], "Forwarder")

    @pytest.fixture
    def simple(self, web3_client, accounts):
        return web3_client.compile_by_vyper_and_deploy(accounts[0], "Simple")

    def test_name(self, erc20_vyper):
        assert erc20_vyper.functions.name().call() == INIT_NAME

    def test_mint(self, erc20_vyper, accounts, web3_client):
        check_erc20_mint_function(web3_client, erc20_vyper, accounts[0])

    def test_transfer(self, erc20_vyper, accounts, web3_client):
        check_erc20_transfer_function(web3_client, erc20_vyper, accounts[0], accounts[1])

    def test_deploy_contract_by_contract(self, simple, forwarder, accounts, web3_client):
        tx = web3_client.make_raw_tx(accounts[0].address, estimate_gas=False)
        instr = forwarder.functions.deploy(simple.address, accounts[0].address).build_transaction(tx)
        resp = web3_client.send_transaction(accounts[0], instr)
        assert resp["status"] == 1
