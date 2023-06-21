import allure
from integration.tests.basic.helpers.basic import BaseMixin


@allure.story("Expected proxy errors during contract calls")
class TestExpectedErrors(BaseMixin):

    def test_bump_allocator_out_of_memory_expected_error(self):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "ExpectedErrorsChecker", "0.8.12", self.sender_account, contract_name="A"
        )

        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = contract.functions.method1().build_transaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        # Error is Bump Allocator out of memory. [1]=- Error: memory allocation failed, out of memory. in proxy log
        assert resp["status"] == 0
