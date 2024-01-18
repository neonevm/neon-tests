import allure
import pytest
from solana.transaction import PublicKey
from hexbytes import HexBytes

from utils.accounts import EthAccounts
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client


@allure.feature("EVM tests")
@allure.story("Verify block hash")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestGetBlockHash:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def test_get_current_block_hash(self, blockhash_contract):
        sender_account = self.accounts[0]
        instruction_tx = blockhash_contract.functions.getCurrentValues().build_transaction(
            {
                "from": sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(sender_account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        assert (
            instruction_receipt["logs"][0]["data"].hex()
            == "0x0000000000000000000000000000000000000000000000000000000000000000"
        )

    def _get_slot_hash(self, number: int) -> HexBytes:
        slot_hashes_id = PublicKey("SysvarS1otHashes111111111111111111111111111")
        account_info = self.sol_client.get_account_info(slot_hashes_id, "confirmed").value
        count = int.from_bytes(account_info.data[:8], "little")
        for i in range(0, count):
            offset = 8 + 40 * i
            slot = int.from_bytes(account_info.data[offset : (offset + 8)], "little")
            if slot != number:
                continue

            return HexBytes(account_info.data[(offset + 8) : (offset + 40)])

        assert False, "Slot not found"

    def test_get_block_hash_from_history(self, blockhash_contract):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        for _ in range(5):
            self.web3_client.send_neon(sender_account, recipient_account, 1)

        current_block_number = self.web3_client.get_block_number()
        block_number_history = current_block_number - 4
        block_hash_history = self._get_slot_hash(block_number_history)

        instruction_tx = blockhash_contract.functions.getValues(block_number_history).build_transaction(
            {
                "from": sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(sender_account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        instruction_receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert instruction_receipt["logs"][0]["data"] == block_hash_history
