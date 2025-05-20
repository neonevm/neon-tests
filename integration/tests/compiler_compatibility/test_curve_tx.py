import pytest
import utils.vyperx as vyperx


class TestVyperCompatibility:
    @pytest.fixture(scope="class", autouse=True)
    def install_vyper(self, request):
        version = "0.1.b16"
        vyperx.install(version)
        print(f"{version} vyper version installed")

    @pytest.fixture
    def curve_v1_vyper(self, web3_client, accounts):
        return web3_client.compile_by_vyper_and_deploy(
            accounts[0],
            "CurveTokenV1",
            [
                "Curve.fi renBTC/wBTC/sBTC",  # _name: String[64]
                "crvRenWSBTC",  # _symbol: String[32]
                18,  # _decimals: uint256
                0,  # _supply: uint256
            ],
        )

    def test_name(self, curve_v1_vyper):
        assert curve_v1_vyper.functions.name().call() == "Curve.fi renBTC/wBTC/sBTC"

    # def test_mint(self, erc20_vyper, accounts, web3_client):
    #     check_erc20_mint_function(web3_client, erc20_vyper, accounts[0])
    #
    # def test_transfer(self, erc20_vyper, accounts, web3_client):
    #     check_erc20_transfer_function(web3_client, erc20_vyper, accounts[0], accounts[1])
    #
    # def test_deploy_contract_by_contract(self, simple, forwarder, accounts, web3_client):
    #     tx = web3_client.make_raw_tx(accounts[0].address, estimate_gas=False)
    #     instr = forwarder.functions.deploy(simple.address, accounts[0].address).build_transaction(tx)
    #     resp = web3_client.send_transaction(accounts[0], instr)
    #     assert resp["status"] == 1
