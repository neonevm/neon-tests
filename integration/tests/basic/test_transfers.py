from re import U
import allure
import pytest
from typing import Union
from integration.tests.basic.helpers.basic import WAITING_FOR_ERC20, WAITING_FOR_MS, BasicTests
from integration.tests.basic.helpers.error_message import ErrorMessage
from integration.tests.basic.model.model import AccountData
from integration.tests.basic.test_data.input_data import InputData

INVALID_ADDRESS = AccountData(address="0x12345")
ENS_NAME_ERROR = f"ENS name: '{INVALID_ADDRESS.address}' is invalid."
EIP55_INVALID_CHECKSUM = "'Address has an invalid EIP-55 checksum. After looking up the address from the original source, try again.'"
U64_MAX = 18_446_744_073_709_551_615

WRONG_TRANSFER_AMOUNT_DATA = [(1_501), (10_000.1)]
TRANSFER_AMOUNT_DATA = [(0.01), (1), (1.1)]

GAS_LIMIT_AND_PRICE_DATA = ([1, (U64_MAX+1)], [1000, int((U64_MAX+100)/1000)])


@allure.story("Basic: transfer tests")
class TestTransfer(BasicTests):
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_neon_from_one_account_to_another(self, amount: Union[int,
                                                                       float],
                                                   prepare_accounts):
        """Send neon from one account to another"""

        tx_receipt = self.process_transaction(self.sender_account,
                                              self.recipient_account, amount)

        self.assert_balance(
            self.sender_account.address,
            InputData.FAUCET_1ST_REQUEST_AMOUNT.value - amount -
            self.calculate_trx_gas(tx_receipt=tx_receipt))
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value + amount)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_send_spl_wrapped_account_from_one_account_to_another(self):
        """Send spl wrapped account from one account to another"""
        pass

    @pytest.mark.parametrize("amount", WRONG_TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_neon(self, amount: Union[int,
                                                                      float],
                                                  prepare_accounts):
        """Send more than exist on account: neon"""

        self.check_value_error_if_less_than_required(self.sender_account,
                                                     self.recipient_account,
                                                     amount)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    @pytest.mark.skip(WAITING_FOR_MS)
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_spl(self, amount):
        """Send more than exist on account: spl (with different precision)"""
        pass

    @pytest.mark.skip(WAITING_FOR_ERC20)
    def test_send_more_than_exist_on_account_erc20(self):
        """Send more than exist on account: ERC20"""
        pass

    def test_zero_neon(self, prepare_accounts):
        """Send zero: neon"""

        tx_receipt = self.process_transaction(self.sender_account,
                                              self.recipient_account)

        self.assert_balance(
            self.sender_account.address,
            InputData.FAUCET_1ST_REQUEST_AMOUNT.value -
            self.calculate_trx_gas(tx_receipt=tx_receipt))
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_zero_spl(self):
        """Send zero: spl (with different precision)"""
        pass

    @pytest.mark.xfail()
    def test_zero_erc20(self):
        """Send zero: ERC20"""
        pass

    def test_send_negative_sum_from_account_neon(self, prepare_accounts):
        """Send negative sum from account: neon"""

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            InputData.NEGATIVE_AMOUNT.value,
            error_message=ErrorMessage.NEGATIVE_VALUE.value)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

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

        self.process_transaction_with_failure(
            sender_account,
            INVALID_ADDRESS,
            InputData.DEFAULT_TRANSFER_AMOUNT.value,
            error_message=ENS_NAME_ERROR)

        self.assert_balance(sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    def test_send_more_token_to_non_existing_address(self):
        """Send token to a non-existing address"""
        sender_account = self.create_account_with_balance()
        recipient_address = AccountData(
            address=sender_account.address.replace('1', '2').replace('3', '4'))

        self.process_transaction_with_failure(
            sender_account,
            recipient_address,
            InputData.DEFAULT_TRANSFER_AMOUNT.value,
            error_message=EIP55_INVALID_CHECKSUM)

        self.assert_balance(sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    """
    20.	Check ERC-1820 transaction (without chain_id in sign)		
    21.	Generate bad sign (when v, r, s over allowed size)		
        There are many known variants of, it's not possible to describe all of them.		
        Below are the simplest:		
    22.	Too low gas_limit		
    23.	Too high gas_limit > u64::max		
    24.	Too high gas_price > u64::max		
    25.	Too high gas_limit * gas_price > u64::max		
    26.	There are not enough Neons for gas fee		
    27.	There are not enough Neons for transfer
    """

    def test_check_erc_1820_transaction(self):
        """Check ERC-1820 transaction (without chain_id in sign)"""
        pass

    def test_generate_bad_sign(self):
        """Generate bad sign (when v, r, s over allowed size)"""
        pass

    def test_too_low_gas_limit(self, prepare_accounts):
        """Too low gas_limit"""
        amount = InputData.DEFAULT_TRANSFER_AMOUNT.value

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            gas=1,
            error_message=ErrorMessage.GAS_LIMIT_REACHED.value)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    def test_not_allowed_gas_limit(self, prepare_accounts):
        """Too low gas_limit"""
        amount = InputData.DEFAULT_TRANSFER_AMOUNT.value

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            gas=0.01,
            error_message=ErrorMessage.INVALID_FIELDS_GAS.value)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    def test_too_high_gas_limit_greater_than_u64_max(self, prepare_accounts):
        """Too high gas_limit > u64::max"""
        amount = InputData.DEFAULT_TRANSFER_AMOUNT.value

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            gas=U64_MAX + 1,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    def test_too_high_gas_price_greater_than_u64_max(self, prepare_accounts):
        """Too high gas_price > u64::max"""
        amount = InputData.DEFAULT_TRANSFER_AMOUNT.value

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            gas_price=U64_MAX + 1,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    @pytest.mark.parametrize("gas_limit,gas_price", GAS_LIMIT_AND_PRICE_DATA)
    def test_too_high_gas_limit_by_gas_prise_greater_than_u64_max(self, gas_limit: float, gas_price: float, prepare_accounts):
        """Too high gas_limit * gas_price > u64::max"""
        sender_amount = 2
        self.sender_account = self.create_account_with_balance(sender_amount)
        self.recipient_account = self.web3_client.create_account()
        amount = InputData.DEFAULT_TRANSFER_AMOUNT.value

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            gas=gas_limit,
            gas_price=gas_price,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value)

        self.assert_balance(self.sender_account.address, sender_amount)
        self.assert_balance(self.recipient_account.address, 0)

    def test_there_are_not_enough_neons_for_gas_fee(self):
        """There are not enough Neons for gas fee"""
        sender_amount = 1
        self.sender_account = self.create_account_with_balance(sender_amount)
        self.recipient_account = self.web3_client.create_account()
        amount = 0.9

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value)

        self.assert_balance(self.sender_account.address, sender_amount)
        self.assert_balance(self.recipient_account.address, 0)

    def test_there_are_not_enough_neons_for_transfer(self):
        """There are not enough Neons for transfer"""
        sender_amount = 1
        self.sender_account = self.create_account_with_balance(sender_amount)
        self.recipient_account = self.web3_client.create_account()
        amount = 1.1

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value)

        self.assert_balance(self.sender_account.address, sender_amount)
        self.assert_balance(self.recipient_account.address, 0)
