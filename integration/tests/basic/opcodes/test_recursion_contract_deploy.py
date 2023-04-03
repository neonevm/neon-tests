import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import generate_text

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@allure.feature("Opcodes verifications")
@allure.story("Recursion contract deploy (create2 opcode)")
class TestContractRecursion(BaseMixin):

    @pytest.fixture(scope="function")
    def first_contract(self):
        contract, trx = self.web3_client.deploy_and_get_contract(
            "Recursion", "0.8.10", self.sender_account,
            contract_name="FirstContract",
            constructor_args=[3])
        return contract

    def test_deploy_with_recursion(self, first_contract):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = first_contract.functions.deploySecondContract().buildTransaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert first_contract.functions.getSecondDeployedContractCount().call() == 3

        event_logs = first_contract.events.SecondContractDeployed().processReceipt(receipt)
        for event_log in event_logs:
            assert event_log["args"]["addr"] != ZERO_ADDRESS

    @pytest.mark.xfail(reason="SA-159")
    def test_deploy_with_recursion_via_create2(self, first_contract):
        tx = self.create_contract_call_tx_object(self.sender_account)
        salt = generate_text(min_len=5, max_len=7)
        instruction_tx = first_contract.functions.deployThirdContractViaCreate2(salt).buildTransaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

        event_logs = first_contract.events.ThirdContractDeployed().processReceipt(receipt)
        addresses = [event_log["args"]["addr"] for event_log in event_logs]
        assert len(addresses) == 1
        assert ZERO_ADDRESS not in addresses

    @pytest.mark.xfail(reason="SA-159")
    def test_deploy_to_the_same_address_via_create2_one_trx(self, first_contract):
        tx = self.create_contract_call_tx_object(self.sender_account)
        salt = generate_text(min_len=5, max_len=7)
        instruction_tx = first_contract.functions.deployViaCreate2Twice(salt).buildTransaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert first_contract.functions.getThirdDeployedContractCount().call() == 2

        event_logs = first_contract.events.ThirdContractDeployed().processReceipt(receipt)
        addresses = [event_log["args"]["addr"] for event_log in event_logs]
        assert ZERO_ADDRESS in addresses

