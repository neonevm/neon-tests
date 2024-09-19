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

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
        try:
            resp = self.web3_client.send_transaction(sender_account, instruction_tx)
            assert resp["status"] == 0
        except ValueError as exc:
            assert "Error: memory allocation failed, out of memory." in exc.args[0]["message"]
