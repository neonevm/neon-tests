import pytest
import sha3
from eth_utils import keccak

from integration.tests.basic.helpers.basic import BaseMixin

facet_cut_action = {"Add": 0, "Replace": 1, "Remove": 2}


def get_selectors(abi):
    """Get topics as keccak256 from abi Events"""
    selectors = []
    print(abi)
    for function in filter(lambda item: item["type"] == "function", abi):
        input_types = ",".join(i["type"] for i in function["inputs"])
        keccak256 = sha3.keccak_256()
        keccak256.update(f"{function['name']}({input_types})".encode())
        selectors.append("0x" + keccak(text=f"{function['name']}({input_types})")[:4].hex())
        # selectors.append(keccak256.hexdigest()[:4])
    return selectors


class TestDiamond(BaseMixin):
    @pytest.fixture(scope="function")
    def diamond_init(self, web3_client):
        contract, _ = web3_client.deploy_and_get_contract(
            "diamond/upgradeInitializers/DiamondInit.sol", "0.8.10", self.sender_account, contract_name="DiamondInit")
        return contract

    @pytest.fixture(scope="function")
    def facet_cuts(self, web3_client, diamond_cut_facet, diamond_loupe_facet, ownership_facet):
        facet_cuts = []
        for facet in [diamond_cut_facet, diamond_loupe_facet, ownership_facet]:
            facet_cuts.append((facet.address, facet_cut_action["Add"], get_selectors(facet.abi)))
        print("facet_cuts", facet_cuts)
        return facet_cuts

    @pytest.fixture(scope="function")
    def diamond_cut_facet(self, web3_client):
        contract, _ = web3_client.deploy_and_get_contract(
            "diamond/facets/DiamondCutFacet.sol", "0.8.10", self.sender_account, contract_name="DiamondCutFacet")
        return contract

    @pytest.fixture(scope="function")
    def diamond_loupe_facet(self, web3_client):
        contract, _ = web3_client.deploy_and_get_contract(
            "diamond/facets/DiamondLoupeFacet.sol", "0.8.10", self.sender_account, contract_name="DiamondLoupeFacet")
        return contract

    @pytest.fixture(scope="function")
    def ownership_facet(self, web3_client):
        contract, _ = web3_client.deploy_and_get_contract(
            "diamond/facets/OwnershipFacet.sol", "0.8.10", self.sender_account, contract_name="OwnershipFacet")
        return contract

    @pytest.fixture(scope="function")
    def diamond(self, web3_client, diamond_init, facet_cuts):
        calldata = "0x" + keccak(text="init()")[:4].hex()
        print("calldata", calldata)
        diamond_args = [self.sender_account.address, diamond_init.address, calldata]
        contract, tx = web3_client.deploy_and_get_contract("diamond/Diamond.sol", "0.8.10", self.sender_account,
                                                           contract_name="Diamond",
                                                           constructor_args=[facet_cuts, diamond_args])
        print(tx)

        return contract

    def test_diamond(self, diamond, facet_cuts, diamond_loupe_facet):
        addresses = diamond_loupe_facet.functions.facetAddresses().call()
        print("addresses", addresses)
        assert addresses == [facet_cuts[0][0], facet_cuts[1][0], facet_cuts[2][0]]
