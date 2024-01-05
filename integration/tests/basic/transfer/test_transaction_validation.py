import random
import re

import allure
import pytest

from integration.tests.basic.helpers.assert_message import ErrorMessage
from integration.tests.basic.helpers.rpc_checks import is_hex
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client
from utils.helpers import gen_hash_of_block

U64_MAX = 18_446_744_073_709_551_615

GAS_LIMIT_AND_PRICE_DATA = (
    [1, None, ErrorMessage.GAS_LIMIT_REACHED.value],
    [U64_MAX + 1, None, ErrorMessage.GAS_OVERFLOW.value],
    [
        10_000,
        U64_MAX + 1,
        ErrorMessage.INSUFFICIENT_FUNDS.value,
    ],
    [1, (U64_MAX + 1), ErrorMessage.GAS_LIMIT_REACHED.value],
    [1_000, int((U64_MAX + 100) / 1_000), ErrorMessage.GAS_LIMIT_REACHED.value],
)


@allure.feature("Ethereum compatibility")
@allure.story("Verify transactions validation")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestTransactionsValidation:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("gas_limit,gas_price,expected_message", GAS_LIMIT_AND_PRICE_DATA)
    def test_generate_bad_sign(self, gas_limit, gas_price, expected_message):
        """Generate bad sign (when v, r, s over allowed size)
        Too low gas_limit
        Too high gas_limit > u64::max
        Too high gas_price > u64::max
        Too high gas_limit * gas_price > u64::max
        """

        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        initial_sender_balance = self.web3_client.get_balance(sender_account)
        initial_recipient_balance = self.web3_client.get_balance(recipient_account)

        with pytest.raises(ValueError, match=expected_message):
            self.web3_client.send_neon(sender_account, recipient_account, amount=1, gas=gas_limit, gas_price=gas_price)

        assert initial_sender_balance == self.web3_client.get_balance(sender_account)
        assert initial_recipient_balance == self.web3_client.get_balance(recipient_account)

    def test_send_underpriced_transaction(self, json_rpc_client):
        """Check that transaction can't be sent if gas value is too small"""
        gas_price = random.randint(0, 10000)

        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]

        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=1, gas_price=gas_price, estimate_gas=True
        )
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        pattern = str.format(ErrorMessage.TRANSACTION_UNDERPRICED.value, gas_price) + r" \d.*"
        assert re.match(pattern, response["error"]["message"])
        assert response["error"]["code"] == -32000

    def test_send_too_big_transaction(self, json_rpc_client):
        """Transaction size is too big"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=1, estimate_gas=True
        )
        transaction["data"] = gen_hash_of_block(256 * 1024)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        params = [signed_tx.rawTransaction.hex()]
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", params)
        assert ErrorMessage.TOO_BIG_TRANSACTION.value in response["error"]["message"]
        assert response["error"]["code"] == -32000

    @pytest.mark.skip(reason="Test doesn't work with MINIMAL_GAS_PRICE in config. NDEV-2386")
    def test_send_transaction_with_small_gas_price(self, new_account, json_rpc_client):
        """Check that transaction can't be accepted if gas value is too small"""
        gas_price = self.web3_client.gas_price()
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=1, gas_price=(int(gas_price * 0.01))
        )
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, new_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        assert is_hex(response["result"])
        self.web3_client.wait_for_transaction_receipt(response["result"])
        receipt = json_rpc_client.send_rpc(method="eth_getTransactionReceipt", params=[response["result"]])
        assert receipt["result"] is None

    def test_big_memory_value(self):
        sender_account = self.accounts[0]
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/BigMemoryValue", "0.8.12", account=sender_account
        )
        bytes_amount = contract.functions.makeBigMemoryValue(5).call()
        assert bytes_amount == 32 * 1024
