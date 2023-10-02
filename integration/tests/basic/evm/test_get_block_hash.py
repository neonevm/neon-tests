import allure

from solana.transaction import PublicKey
from hexbytes import HexBytes

from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("EVM tests")
@allure.story("Verify block hash")
class TestGetBlockHash(BaseMixin):
    def test_get_current_block_hash(self):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "BlockHash",
            "0.8.10",
            contract_name="BlockHashTest",
            account=self.sender_account,
        )

        instruction_tx = contract.functions.getCurrentValues().build_transaction(
            {
                "from": self.sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.sender_account.address
                ),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(
            self.sender_account, instruction_tx
        )

        assert (
            instruction_receipt["logs"][0]["data"].hex()
            == "0x0000000000000000000000000000000000000000000000000000000000000000"
        )

    def _get_slot_hash(self, number: int) -> HexBytes:
        slot_hashes_id = PublicKey("SysvarS1otHashes111111111111111111111111111")
        account_info = self.sol_client.get_account_info(
            slot_hashes_id, "confirmed"
        ).value
        count = int.from_bytes(account_info.data[:8], "little")
        for i in range(0, count):
            offset = 8 + 40 * i
            slot = int.from_bytes(account_info.data[offset : (offset + 8)], "little")
            if slot != number:
                continue

            return HexBytes(account_info.data[(offset + 8) : (offset + 40)])

        assert False, "Slot not found"

    def test_get_block_hash_from_history(self):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "BlockHash",
            "0.8.10",
            contract_name="BlockHashTest",
            account=self.sender_account,
        )
        for _ in range(5):
            self.send_neon(self.sender_account, self.recipient_account, 1)

        current_block_number = self.web3_client.get_block_number()
        block_number_history = current_block_number - 4
        block_hash_history = self._get_slot_hash(block_number_history)

        instruction_tx = contract.functions.getValues(
            block_number_history
        ).build_transaction(
            {
                "from": self.sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.sender_account.address
                ),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(
            self.sender_account, instruction_tx
        )
        assert instruction_receipt["logs"][0]["data"] == block_hash_history
