import pytest
import solcx
import web3
import web3.exceptions
from semantic_version import Version

import allure
from integration.tests.basic.helpers.assert_message import ErrorMessage
from utils.accounts import EthAccounts
from utils.helpers import cryptohex, get_contract_abi, int_to_hex
from utils.web3client import NeonChainWeb3Client


@allure.feature("Ethereum compatibility")
@allure.story("Contract Reverting")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestContractReverting:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def solc_version(self) -> Version:
        return solcx.install_solc("0.7.0")

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
        contract = self.web3_client.eth.contract(abi=contract_interface["abi"], bytecode=contract_interface["bin"])
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
        contract = self.web3_client.eth.contract(abi=contract_interface["abi"], bytecode=contract_interface["bin"])

        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted"):
            contract.constructor([]).build_transaction()

    def test_method_raises_string_based_error(self, revert_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)

        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted: Predefined revert happened"):
            revert_contract.functions.doStringBasedRevert().build_transaction(tx)

        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="execution reverted: Predefined revert happened",
        ):
            revert_contract.functions.doStringBasedRevert().call()

    def test_method_raises_trivial_error(self, revert_contract):
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted"):
            revert_contract.functions.doTrivialRevert().call()

    def test_nested_contract_revert(self, revert_contract):
        sender_account = self.accounts[0]
        contract, _ = self.web3_client.deploy_and_get_contract(
            contract="common/Revert",
            version="0.8.10",
            contract_name="Caller",
            account=sender_account,
            constructor_args=[revert_contract.address],
        )
        tx = self.web3_client.make_raw_tx(sender_account)
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted: Predefined revert happened"):
            contract.functions.doStringBasedRevert().build_transaction(tx)

    def test_eth_call_revert(self, revert_contract):
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="execution reverted: Predefined revert happened",
        ):
            revert_contract.functions.doStringBasedRevert().call()

    def test_gas_limit_reached(self, revert_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, amount=1)
        tx["gas"] = 1  # setting low level of gas limit to get the error
        instruction_tx = revert_contract.functions.deposit().build_transaction(tx)
        with pytest.raises(ValueError, match=ErrorMessage.GAS_LIMIT_REACHED.value):
            self.web3_client.send_transaction(sender_account, instruction_tx)

    def test_custom_error_revert(self, revert_contract):
        params = [1, 2]

        with pytest.raises(
            web3.exceptions.ContractCustomError,
            match=cryptohex("NumberTooHigh(uint256,uint256)")[:10] + int_to_hex(params[0]) + int_to_hex(params[1]),
        ):
            revert_contract.functions.customErrorRevert(params[0], params[1]).build_transaction()

    def test_assert_revert(self, revert_contract):
        with pytest.raises(web3.exceptions.ContractPanicError, match="Panic error 0x01: Assert evaluates to false"):
            revert_contract.functions.doAssert().call()

    def test_method_raises_string_based_error_caller(self, revert_contract_caller):
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="execution reverted: Predefined revert happened",
        ):
            revert_contract_caller.functions.doStringBasedRevert().call()

    def test_method_raises_string_based_error_tx_caller(self, revert_contract_caller):
        tx = self.web3_client.make_raw_tx(self.accounts[0])
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted: Predefined revert happened"):
            revert_contract_caller.functions.doStringBasedRevert().build_transaction(tx)

    def test_method_raises_string_based_error_tx_with_gas_caller(self, revert_contract_caller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.doStringBasedRevert().build_transaction(tx)
        assert self.web3_client.send_transaction(sender_account, instruction_tx)["status"] == 0

    def test_method_raises_trivial_error_caller(self, revert_contract_caller):
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted"):
            revert_contract_caller.functions.doTrivialRevert().call()

    def test_method_raises_trivial_error_tx_caller(self, revert_contract_caller):
        tx = self.web3_client.make_raw_tx(self.accounts[0])
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted"):
            revert_contract_caller.functions.doTrivialRevert().build_transaction(tx)

    def test_method_raises_trivial_error_tx_with_gas_caller(self, revert_contract_caller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.doTrivialRevert().build_transaction(tx)
        assert self.web3_client.send_transaction(sender_account, instruction_tx)["status"] == 0

    def test_custom_error_revert_caller(self, revert_contract_caller):
        params = [1, 2]
        with pytest.raises(
            web3.exceptions.ContractCustomError,
            match=cryptohex("NumberTooHigh(uint256,uint256)")[:10] + int_to_hex(params[0]) + int_to_hex(params[1]),
        ):
            revert_contract_caller.functions.doCustomErrorRevert(params[0], params[1]).call()

    def test_custom_error_revert_tx_caller(self, revert_contract_caller):
        params = [1, 2]
        with pytest.raises(
            web3.exceptions.ContractCustomError,
            match=cryptohex("NumberTooHigh(uint256,uint256)")[:10] + int_to_hex(params[0]) + int_to_hex(params[1]),
        ):
            revert_contract_caller.functions.doCustomErrorRevert(params[0], params[1]).build_transaction()

    def test_custom_error_revert_tx_with_gas_caller(self, revert_contract_caller):
        params = [1, 2]
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.doCustomErrorRevert(params[0], params[1]).build_transaction(
            tx
        )
        assert self.web3_client.send_transaction(sender_account, instruction_tx)["status"] == 0

    def test_assert_revert_caller(self, revert_contract_caller):
        with pytest.raises(web3.exceptions.ContractPanicError, match="Panic error 0x01: Assert evaluates to false"):
            revert_contract_caller.functions.doAssert().call()

    def test_assert_revert_tx_caller(self, revert_contract_caller):
        tx = self.web3_client.make_raw_tx(self.accounts[0])
        with pytest.raises(web3.exceptions.ContractPanicError, match="Panic error 0x01: Assert evaluates to false"):
            revert_contract_caller.functions.doAssert().build_transaction(tx)

    def test_assert_revert_tx_with_gas_caller(self, revert_contract_caller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.doAssert().build_transaction(tx)
        assert self.web3_client.send_transaction(sender_account, instruction_tx)["status"] == 0

    def test_deploy_failed_contract_caller(self, revert_contract_caller):
        with pytest.raises(
            web3.exceptions.ContractLogicError, match="'execution reverted: Constructor intentionally failed"
        ):
            revert_contract_caller.functions.deployContract().call()

    def test_deploy_failed_contract_tx_caller(self, revert_contract_caller):
        tx = self.web3_client.make_raw_tx(self.accounts[0])
        with pytest.raises(
            web3.exceptions.ContractLogicError, match="'execution reverted: Constructor intentionally failed"
        ):
            revert_contract_caller.functions.deployContract().build_transaction(tx)

    def test_deploy_failed_contract_tx_with_gas_caller(self, revert_contract_caller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.deployContract().build_transaction(tx)
        assert self.web3_client.send_transaction(sender_account, instruction_tx)["status"] == 0

    def test_contract_memory_overflow_call(self, accounts):
        _, trx_id = self.web3_client.deploy_and_get_contract(
            contract="common/Overflow", version="0.5.0", contract_name="TestDef", account=accounts[0]
        )
        assert trx_id["status"] == 1
