import allure
import pytest
import solcx
import web3
import web3.exceptions

from integration.tests.basic.helpers.assert_message import ErrorMessage
from integration.tests.basic.helpers.basic import BaseMixin, Tag
from utils.helpers import get_contract_abi


@pytest.fixture(scope="class")
def revert_contract(web3_client, class_account):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Revert", version="0.8.10",
        contract_name="TrivialRevert", account=class_account,
    )
    yield contract


@allure.feature("Ethereum compatibility")
@allure.story("Contract Reverting")
class TestContractReverting(BaseMixin):
    @pytest.fixture(scope="class")
    def solc_version(self):
        version = "0.7.0"
        if version not in [str(v) for v in solcx.get_installed_solc_versions()]:
            solcx.install_solc(version)
        return version

    def test_constructor_raises_string_based_error(self, solc_version):
        contract = """
            pragma solidity >=0.7.0 <0.9.0;
            contract ArrConstructable {
                constructor(uint256[] memory vector_) payable {
                    require(vector_.length > 0, "ListConstructable: empty list");
                }
            }
        """
        compiled = solcx.compile_source(
            contract, output_values=["abi", "bin"], solc_version=solc_version
        )  # this allow_paths isn't very good...
        contract_interface = get_contract_abi("ArrConstructable", compiled)
        contract = self.web3_client.eth.contract(
            abi=contract_interface["abi"], bytecode=contract_interface["bin"]
        )
        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="execution reverted: ListConstructable: empty list",
        ):
            contract.constructor([]).build_transaction()

    def test_constructor_raises_no_argument_error(self, solc_version):
        contract = """
            pragma solidity >=0.7.0 <0.9.0;
            contract ArrConstructable {
                constructor(uint256[] memory vector_) payable {
                    require(vector_.length > 0);
                }
            }
        """

        compiled = solcx.compile_source(
            contract, output_values=["abi", "bin"], solc_version=solc_version
        )  # this allow_paths isn't very good...
        contract_interface = get_contract_abi("ArrConstructable", compiled)
        contract = self.web3_client.eth.contract(
            abi=contract_interface["abi"], bytecode=contract_interface["bin"]
        )

        with pytest.raises(
                web3.exceptions.ContractLogicError, match="execution reverted"
        ):
            contract.constructor([]).build_transaction()

    def test_method_raises_string_based_error(self, revert_contract):
        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="execution reverted: Predefined revert happened",
        ):
            revert_contract.functions.doStringBasedRevert().call()

    def test_method_raises_trivial_error(self, revert_contract):
        with pytest.raises(
                web3.exceptions.ContractLogicError, match="execution reverted"
        ):
            revert_contract.functions.doTrivialRevert().call()

    def test_nested_contract_revert(self, revert_contract):
        contract, _ = self.web3_client.deploy_and_get_contract(
            contract="common/Revert", version="0.8.10",
            contract_name="Caller", account=self.sender_account,
            constructor_args=[revert_contract.address]
        )
        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="execution reverted: Predefined revert happened"
        ):
            tx = self.make_contract_tx_object()
            instruction_tx = contract.functions.doStringBasedRevert().build_transaction(tx)
            self.web3_client.send_transaction(self.sender_account, instruction_tx)

    def test_eth_call_revert(self, revert_contract):
        tx = {
            "from": self.sender_account.address,
            "to": revert_contract.address,
            "data": revert_contract.encodeABI(fn_name="doStringBasedRevert")
        }
        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="execution reverted: Predefined revert happened"
        ):
            self.web3_client._web3.eth.call(tx, Tag.LATEST.value)

    def test_gas_limit_reached(self, revert_contract, class_account):
        tx = self.make_contract_tx_object(amount=1)
        tx["gas"] = 1  # setting low level of gas limit to get the error
        instruction_tx = revert_contract.functions.deposit().build_transaction(tx)
        with pytest.raises(
                ValueError,
                match=ErrorMessage.GAS_LIMIT_REACHED.value
        ):
            self.web3_client.send_transaction(self.sender_account, instruction_tx)

    def test_custom_error_revert(self, revert_contract):
        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="execution reverted"
        ):
            revert_contract.functions.customErrorRevert(1, 2).call()

    def test_assert_revert(self, revert_contract):
        with pytest.raises(
                web3.exceptions.ContractLogicError,
                match="execution reverted"
        ):
            revert_contract.functions.doAssert().call()
