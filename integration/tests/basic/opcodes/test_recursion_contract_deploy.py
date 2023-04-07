import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import generate_text

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@allure.feature("Opcodes verifications")
@allure.story("Recursion contract deploy (create2 opcode)")
class TestContractRecursion(BaseMixin):

    @pytest.fixture(scope="function")
    def recursion_factory(self):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "Recursion", "0.8.10", self.sender_account,
            contract_name="DeployRecursionFactory",
            constructor_args=[3])
        return contract

    def test_deploy_with_recursion(self, recursion_factory):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = recursion_factory.functions.deployFirstContract().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert recursion_factory.functions.getFirstDeployedContractCount().call() == 3

        event_logs = recursion_factory.events.FirstContractDeployed().process_receipt(receipt)
        for event_log in event_logs:
            assert event_log["args"]["addr"] != ZERO_ADDRESS

    def test_deploy_with_recursion_via_create2(self, recursion_factory):
        tx = self.create_contract_call_tx_object(self.sender_account)
        salt = generate_text(min_len=5, max_len=7)
        instruction_tx = recursion_factory.functions.deploySecondContractViaCreate2(salt).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

        event_logs = recursion_factory.events.SecondContractDeployed().process_receipt(receipt)
        addresses = [event_log["args"]["addr"] for event_log in event_logs]
        assert len(addresses) == 1
        assert ZERO_ADDRESS not in addresses

    def test_deploy_with_recursion_via_create(self, recursion_factory):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = recursion_factory.functions.deployFirstContractViaCreate().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

        event_logs = recursion_factory.events.FirstContractDeployed().process_receipt(receipt)
        addresses = [event_log["args"]["addr"] for event_log in event_logs]
        assert len(addresses) == 3
        assert ZERO_ADDRESS not in addresses

    def test_deploy_to_the_same_address_via_create2_one_trx(self, recursion_factory):
        tx = self.create_contract_call_tx_object(self.sender_account)
        salt = generate_text(min_len=5, max_len=7)
        instruction_tx = recursion_factory.functions.deployViaCreate2Twice(salt).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert recursion_factory.functions.getSecondDeployedContractCount().call() == 2

        event_logs = recursion_factory.events.SecondContractDeployed().process_receipt(receipt)
        addresses = [event_log["args"]["addr"] for event_log in event_logs]
        assert ZERO_ADDRESS in addresses

    def test_recursion_in_function_calls(self):
        contract_caller2, _ = self.web3_client.deploy_and_get_contract(
            "Recursion", "0.8.10", self.sender_account,
            contract_name="RecursionCaller2")
        depth = 5
        contract_caller1, _ = self.web3_client.deploy_and_get_contract(
            "Recursion", "0.8.10", self.sender_account,
            contract_name="RecursionCaller1",
            constructor_args=[depth, contract_caller2.address, False])
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = contract_caller1.functions.callContract2().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        event_logs = contract_caller1.events.SecondContractCalled().process_receipt(receipt)
        assert len(event_logs) == depth
        results = [event_log["args"]["result"] for event_log in event_logs]
        assert False not in results

    def test_recursion_in_constructor_calls(self):
        contract_caller2, _ = self.web3_client.deploy_and_get_contract(
            "Recursion", "0.8.10", self.sender_account,
            contract_name="RecursionCaller2")
        contract_caller1, _ = self.web3_client.deploy_and_get_contract(
            "Recursion", "0.8.10", self.sender_account,
            contract_name="RecursionCaller1",
            constructor_args=[5, contract_caller2.address, True])

        assert contract_caller1.functions.depth().call() == 0
