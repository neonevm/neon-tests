import allure

from integration.tests.basic.helpers.basic import BaseMixin


@allure.story("Basic: get block hash through a contract")
class TestGetBlockHash(BaseMixin):

    def test_get_current_block_hash(self):
        contract, _ = self.web3_client.deploy_and_get_contract("BlockHash", "0.8.10", contract_name="BlockHashTest",
                                                               account=self.sender_account)

        instruction_tx = contract.functions.getCurrentValues().buildTransaction(
            {
                "from": self.sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert instruction_receipt['logs'][0][
                   'data'] == '0x0000000000000000000000000000000000000000000000000000000000000000'

    def test_get_block_hash_from_history(self):
        contract, _ = self.web3_client.deploy_and_get_contract("BlockHash", "0.8.10", contract_name="BlockHashTest",
                                                               account=self.sender_account)
        current_block_number = self.web3_client.get_block_number()
        block_number_history = max(int(str(current_block_number), 0) - 25, 1)
        block_hash_history = self.web3_client.get_block_number_by_id(block_number_history).hash

        instruction_tx = contract.functions.getValues(block_number_history).buildTransaction(
            {
                "from": self.sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert instruction_receipt['logs'][0]['data'] == block_hash_history.hex()
