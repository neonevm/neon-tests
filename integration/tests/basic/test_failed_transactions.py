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
        try:
            resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
            assert resp["status"] == 0
        except ValueError as exc:
            assert exc.args[0] == {
                'code': -32000,
                'message': (
                        '[0]>+ ComputeBudget. ' +
                        '[0]>+ ComputeBudget. ' +
                        '[0]>+ NeonEVM. ' +
                        '[1]=- Instruction: Begin or Continue Transaction from Instruction. ' +
                        '[1]=- Bump Allocator out of memory. ' +
                        '[1]=- Error: memory allocation failed, out of memory. ' +
                        '[1]=- BPF program panicked. ' +
                        '[1]<- Program failed to complete'
                )
            }

        # Error is Bump Allocator out of memory. [1]=- Error: memory allocation failed, out of memory. in proxy log

