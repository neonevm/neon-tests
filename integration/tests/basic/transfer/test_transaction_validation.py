import random
import re
import time

import allure
import pytest

from integration.tests.basic.helpers.assert_message import ErrorMessage
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.rpc_checks import is_hex
from utils.consts import InputTestConstants
from utils.helpers import gen_hash_of_block

U64_MAX = 18_446_744_073_709_551_615

GAS_LIMIT_AND_PRICE_DATA = (
    [1, None, ErrorMessage.GAS_LIMIT_REACHED.value],
    [U64_MAX + 1, None, ErrorMessage.GAS_OVERFLOW.value],
    [
        0,
        U64_MAX + 1,
        ErrorMessage.INSUFFICIENT_FUNDS.value,
    ],
    [1, (U64_MAX + 1), ErrorMessage.GAS_LIMIT_REACHED.value],
    [1_000, int((U64_MAX + 100) / 1_000), ErrorMessage.GAS_LIMIT_REACHED.value],
)


@allure.feature("Ethereum compatibility")
@allure.story("Verify transactions validation")
class TestTransactionsValidation(BaseMixin):
    @pytest.mark.parametrize(
        "gas_limit,gas_price,expected_message", GAS_LIMIT_AND_PRICE_DATA
    )
    def test_generate_bad_sign(self, gas_limit, gas_price, expected_message):
        """Generate bad sign (when v, r, s over allowed size)
        Too low gas_limit
        Too high gas_limit > u64::max
        Too high gas_limit > u64::max
        Too high gas_price > u64::max
        Too high gas_limit * gas_price > u64::max
        """

        amount = 100
        sender_account = self.create_account_with_balance(amount)
        recipient_account = self.create_account_with_balance()

        self.send_neon_with_failure(
            sender_account=sender_account,
            recipient_account=recipient_account,
            amount=InputTestConstants.DEFAULT_TRANSFER_AMOUNT.value,
            gas=gas_limit,
            gas_price=gas_price,
            error_message=expected_message,
        )

        self.assert_balance(sender_account.address, amount)
        self.assert_balance(
            recipient_account.address,
            InputTestConstants.FAUCET_1ST_REQUEST_AMOUNT.value,
        )

    def test_send_underpriced_transaction(self):
        """Check that transaction can't be sent if gas value is too small"""
        gas_price = random.randint(0, 10000)
        transaction = self.create_tx_object(gas_price=gas_price)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        pattern = (
                str.format(ErrorMessage.TRANSACTION_UNDERPRICED.value, gas_price) + r" \d.*"
        )
        assert re.match(pattern, response["error"]["message"])
        assert response["error"]["code"] == -32000

    def test_send_too_big_transaction(self):
        """Transaction size is too big"""
        transaction = self.create_tx_object()
        transaction["data"] = gen_hash_of_block(256 * 1024)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        params = [signed_tx.rawTransaction.hex()]
        response = self.proxy_api.send_rpc("eth_sendRawTransaction", params)
        assert ErrorMessage.TOO_BIG_TRANSACTION.value in response["error"]["message"]
        assert response["error"]["code"] == -32000

    @pytest.mark.skip(reason="Test doesn't work with MINIMAL_GAS_PRICE in config. It should be fixed after adding "
                             "different parameters for different chains")
    def test_send_transaction_with_small_gas_price(self, new_account):
        """Check that transaction can't be accepted if gas value is too small"""
        gas_price = self.web3_client.gas_price()
        transaction = self.create_tx_object(sender=new_account.address, gas_price=(int(gas_price * 0.01)))
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, new_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        assert is_hex(response['result'])
        time.sleep(5)
        receipt = self.proxy_api.send_rpc(method="eth_getTransactionReceipt", params=[response["result"]])
        assert receipt['result'] is None

    def test_big_memory_value(self):
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/BigMemoryValue", "0.8.12", account=self.sender_account
        )
        bytes_amount = contract.functions.makeBigMemoryValue(5).call()
        assert bytes_amount == 32 * 1024
