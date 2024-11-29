import pytest
import allure

from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts


@allure.story("Expected proxy errors during contract calls")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestExpectedErrors:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_bump_allocator_out_of_memory_expected_error(self, expected_error_checker):
        sender_account = self.accounts[0]
        balance_before = self.web3_client.get_balance(sender_account)
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
        try:
            receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
            assert receipt["status"] == 0
            balance_after = self.web3_client.get_balance(sender_account.address)
            gas_used = int(receipt["gasUsed"])
            gas_price = int(receipt["effectiveGasPrice"])
            total_fee_paid = gas_used * gas_price
            assert balance_before - balance_after == total_fee_paid
        except ValueError as exc:
            assert "Error: memory allocation failed, out of memory." in exc.args[0]["message"]
