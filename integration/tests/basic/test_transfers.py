from typing import Union

import allure
import pytest

from integration.tests.basic.helpers.basic import WAITING_FOR_ERC20, WAITING_FOR_MS, BaseMixin
from integration.tests.basic.helpers.error_message import ErrorMessage
from integration.tests.basic.model.model import AccountData
from integration.tests.basic.test_data.input_data import InputData

INVALID_ADDRESS = AccountData(address="0x12345")
ENS_NAME_ERROR = f"ENS name: '{INVALID_ADDRESS.address}' is invalid."
EIP55_INVALID_CHECKUM = (
    "'Address has an invalid EIP-55 checksum. After looking up the address from the original source, try again.'"
)

WRONG_TRANSFER_AMOUNT_DATA = [(11000_501), (10000_000.1)]
TRANSFER_AMOUNT_DATA = [(0.01), (1), (1.1)]


@allure.story("Basic: transfer tests")
class TestTransfer(BaseMixin):
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_neon_from_one_account_to_another(self, amount: Union[int, float]):
        """Send neon from one account to another"""
        sender_balance = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))
        tx_receipt = self.transfer_neon(self.sender_account, self.recipient_account, amount)
        self.assert_balance(
            self.sender_account.address,
            sender_balance - amount - self.calculate_trx_gas(tx_receipt=tx_receipt),
            rnd_dig=1,
        )
        self.assert_balance(self.recipient_account.address, recipient_balance + amount, rnd_dig=1)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_send_spl_wrapped_account_from_one_account_to_another(self):
        """Send spl wrapped account from one account to another"""
        pass

    @pytest.mark.parametrize("amount", WRONG_TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_neon(self, amount: Union[int, float]):
        """Send more than exist on account: neon"""

        sender_balance = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))
        self.check_value_error_if_less_than_required(self.sender_account, self.recipient_account, amount)

        self.assert_balance(self.sender_account.address, sender_balance, rnd_dig=1)
        self.assert_balance(self.recipient_account.address, recipient_balance, rnd_dig=1)

    @pytest.mark.skip(WAITING_FOR_MS)
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_spl(self, amount):
        """Send more than exist on account: spl (with different precision)"""
        pass

    @pytest.mark.skip(WAITING_FOR_ERC20)
    def test_send_more_than_exist_on_account_erc20(self):
        """Send more than exist on account: ERC20"""
        pass

    def test_zero_neon(self):
        """Send zero: neon"""

        sender_balance = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))
        tx_receipt = self.process_transaction(self.sender_account, self.recipient_account)

        self.assert_balance(
            self.sender_account.address, sender_balance - self.calculate_trx_gas(tx_receipt=tx_receipt), rnd_dig=1
        )
        self.assert_balance(self.recipient_account.address, recipient_balance, rnd_dig=1)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_zero_spl(self):
        """Send zero: spl (with different precision)"""
        pass

    @pytest.mark.xfail()
    def test_zero_erc20(self):
        """Send zero: ERC20"""
        pass

    def test_send_negative_sum_from_account_neon(self):
        """Send negative sum from account: neon"""

        sender_balance = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))
        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            InputData.NEGATIVE_AMOUNT.value,
            ErrorMessage.NEGATIVE_VALUE.value,
        )

        self.assert_balance(self.sender_account.address, sender_balance, rnd_dig=1)
        self.assert_balance(self.recipient_account.address, recipient_balance, rnd_dig=1)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_send_negative_sum_from_account_spl(self):
        """Send negative sum from account: spl (with different precision)"""
        pass

    @pytest.mark.skip(WAITING_FOR_ERC20)
    def test_send_negative_sum_from_account_erc20(self):
        """Send negative sum from account: ERC20"""
        pass

    def test_send_token_to_an_invalid_address(self):
        """Send token to an invalid address"""
        sender_account = self.create_account_with_balance()
        balance_before = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        self.process_transaction_with_failure(
            sender_account, INVALID_ADDRESS, InputData.DEFAULT_TRANSFER_AMOUNT.value, ENS_NAME_ERROR
        )
        balance_after = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))

        assert balance_before == balance_after

    def test_send_more_token_to_non_existing_address(self):
        """Send token to a non-existing address"""
        sender_account = self.create_account_with_balance()
        recipient_address = AccountData(address=sender_account.address.replace("1", "2").replace("3", "4"))

        balance_before = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        self.process_transaction_with_failure(
            sender_account, recipient_address, InputData.DEFAULT_TRANSFER_AMOUNT.value, EIP55_INVALID_CHECKUM
        )
        balance_after = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        assert balance_before == balance_after
