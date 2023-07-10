import allure
import pytest
import web3

from integration.tests.basic.helpers.basic import BaseMixin



@allure.feature("Opcodes verifications")
@allure.story("Go-etherium opCodes tests")
class TestOpCodes(BaseMixin):
    @pytest.fixture(scope="class")
    def opcodes_checker(self, web3_client, faucet, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "OpCodes", "0.5.16", class_account, contract_name="OpCodes")
        return contract

    def test_base_opcodes(self, opcodes_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = opcodes_checker.functions.test().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

    def test_stop(self, opcodes_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = opcodes_checker.functions.test_stop().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

    def test_invalid_opcode(self, opcodes_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        with pytest.raises(web3.exceptions.ContractLogicError, match="EVM encountered invalid opcode"):
            opcodes_checker.functions.test_invalid().build_transaction(tx)

    def test_revert(self, opcodes_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        with pytest.raises(web3.exceptions.ContractLogicError, match="execution reverted"):
            opcodes_checker.functions.test_revert().build_transaction(tx)
