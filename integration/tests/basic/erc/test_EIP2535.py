import allure
import pytest
from eth_abi import abi
from eth_utils import keccak
from web3.exceptions import ContractLogicError

from utils.consts import ZERO_ADDRESS
from utils.helpers import get_selectors, decode_function_signature

from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts

facet_cut_action = {"Add": 0, "Replace": 1, "Remove": 2}


@allure.feature("EIP Verifications")
@allure.story("EIP-2535: Diamonds, Multi-Facet Proxy")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestDiamond:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def diamond_init(self, web3_client_session, class_account):
        contract, _ = web3_client_session.deploy_and_get_contract(
            "EIPs/EIP2535/upgradeInitializers/DiamondInit.sol",
            "0.8.10",
            class_account,
            contract_name="DiamondInit",
        )
        return contract

    @pytest.fixture(scope="class")
    def facet_cuts(self, diamond_cut_facet, diamond_loupe_facet, ownership_facet):
        facet_cuts = []
        for facet in [diamond_cut_facet, diamond_loupe_facet, ownership_facet]:
            facet_cuts.append((facet.address, facet_cut_action["Add"], get_selectors(facet.abi)))
        return facet_cuts

    @pytest.fixture(scope="class")
    def diamond_cut_facet(self, web3_client_session, class_account):
        contract, _ = web3_client_session.deploy_and_get_contract(
            "EIPs/EIP2535/facets/DiamondCutFacet",
            "0.8.10",
            class_account,
            contract_name="DiamondCutFacet",
        )
        return contract

    @pytest.fixture(scope="class")
    def diamond_loupe_facet(self, web3_client_session, class_account):
        contract, _ = web3_client_session.deploy_and_get_contract(
            "EIPs/EIP2535/facets/DiamondLoupeFacet.sol",
            "0.8.10",
            class_account,
            contract_name="DiamondLoupeFacet",
        )
        return contract

    @pytest.fixture(scope="class")
    def ownership_facet(self, web3_client_session, class_account):
        contract, _ = web3_client_session.deploy_and_get_contract(
            "EIPs/EIP2535/facets/OwnershipFacet",
            "0.8.10",
            class_account,
            contract_name="OwnershipFacet",
        )
        return contract

    @pytest.fixture(scope="class")
    def diamond(self, web3_client_session, diamond_init, facet_cuts, class_account):
        calldata = decode_function_signature("init()")
        diamond_args = [class_account.address, diamond_init.address, calldata]
        contract, tx = web3_client_session.deploy_and_get_contract(
            "EIPs/EIP2535/Diamond",
            "0.8.10",
            class_account,
            contract_name="Diamond",
            constructor_args=[facet_cuts, diamond_args],
        )
        return contract

    def test_facet_addresses(self, diamond, facet_cuts):
        addresses = self.web3_client.call_function_at_address(diamond.address, "facetAddresses()", None, ["address[]"])
        assert len(addresses) == 3
        for i in range(3):
            assert addresses[i] == facet_cuts[i][0].lower()

    def test_facet_function_selectors(self, diamond, diamond_loupe_facet, diamond_cut_facet, ownership_facet):
        for facet in [diamond_loupe_facet, diamond_cut_facet, ownership_facet]:
            result = self.web3_client.call_function_at_address(
                diamond.address,
                "facetFunctionSelectors(address)",
                [facet.address],
                ["bytes4[]"],
            )
            selectors = get_selectors(facet.abi)
            for i in range(len(result)):
                assert result[i] == selectors[i]

    def test_add_and_remove_function(self, diamond, diamond_cut_facet, class_account):
        new_facet, _ = self.web3_client.deploy_and_get_contract(
            "EIPs/EIP2535/facets/Test1Facet",
            "0.8.10",
            class_account,
            contract_name="Test1Facet",
        )
        facet_cuts = [(new_facet.address, facet_cut_action["Add"], get_selectors(new_facet.abi))]
        calldata = keccak(text="diamondCut((address,uint8,bytes4[])[],address,bytes)")[:4] + abi.encode(
            ["(address,uint8,bytes4[])[]", "address", "bytes"],
            [facet_cuts, ZERO_ADDRESS, b"0x"],
        )

        tx = self.web3_client.make_raw_tx(class_account, diamond.address, 0, data=calldata, estimate_gas=True)
        self.web3_client.send_transaction(class_account, tx)
        result = self.web3_client.call_function_at_address(
            diamond.address,
            "facetFunctionSelectors(address)",
            [new_facet.address],
            ["bytes4[]"],
        )
        assert set(get_selectors(new_facet.abi)) - set(result) == set(), "selectors not added"
        result = self.web3_client.call_function_at_address(diamond.address, "test1Func10()", None, ["string"])
        assert result == "hello"

        functions_to_keep = ["test1Func2()", "test1Func11()", "test1Func12()"]
        remove_selectors = get_selectors(new_facet.abi)
        for func in functions_to_keep:
            remove_selectors.remove(keccak(text=func)[:4])
        facet_cuts = [(ZERO_ADDRESS, facet_cut_action["Remove"], remove_selectors)]
        calldata = keccak(text="diamondCut((address,uint8,bytes4[])[],address,bytes)")[:4] + abi.encode(
            ["(address,uint8,bytes4[])[]", "address", "bytes"],
            [facet_cuts, ZERO_ADDRESS, b"0x"],
        )

        tx = self.web3_client.make_raw_tx(class_account, diamond.address, 0, data=calldata, estimate_gas=True)
        self.web3_client.send_transaction(class_account, tx)

        result = self.web3_client.call_function_at_address(
            diamond.address,
            "facetFunctionSelectors(address)",
            [new_facet.address],
            ["bytes4[]"],
        )
        assert set(get_selectors(new_facet.abi)) - set(remove_selectors) == set(result), "selectors not removed"
        with pytest.raises(ContractLogicError):
            self.web3_client.call_function_at_address(diamond.address, "test1Func10()", None, ["string"])
