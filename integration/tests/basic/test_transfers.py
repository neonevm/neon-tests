import allure
import pytest
from typing import Union
from integration.tests.basic.helpers.helper_methods import DEFAULT_TRANSFER_AMOUNT, FIRST_FAUCET_REQUEST_AMOUNT, \
    GREAT_AMOUNT, WAITING_FOR_MS, \
    BasicHelpers

WRONG_TRANSFER_AMOUNT_DATA = [(10), (100), (10.1)]
TRANSFER_AMOUNT_DATA = [(0.01), (1), (1.1)]


@allure.story("Basic: transfer tests")
class TestTransfer(BasicHelpers):
    @allure.step("test: send neon from one account to another")
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_neon_from_one_account_to_another(self, amount: Union[int,
                                                                       float]):
        '''Send neon from one account to another'''
        sender_account = self.create_account_with_balance(GREAT_AMOUNT)
        recipient_account = self.create_account_with_balance(
            FIRST_FAUCET_REQUEST_AMOUNT)

        self.transfer_neon(sender_account,
                           recipient_account,
                           amount,
                           gas=10_000,
                           gas_price=1_000_000_000)

        self.assert_sender_amount(sender_account.address,
                                  GREAT_AMOUNT - amount)
        self.assert_recipient_amount(recipient_account.address,
                                     FIRST_FAUCET_REQUEST_AMOUNT + amount)

    @pytest.mark.skip("not yet done")
    @allure.step("test: send spl wrapped account from one account to another")
    def test_send_spl_wrapped_account_from_one_account_to_another(self):
        '''Send spl wrapped account from one account to another'''
        pass

    @allure.step("test: send more than exist on account: neon")
    @pytest.mark.parametrize("amount", WRONG_TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_neon(self, amount: Union[int,
                                                                      float]):
        '''Send more than exist on account: neon'''
        sender_account = self.create_account_with_balance(
            FIRST_FAUCET_REQUEST_AMOUNT)
        recipient_account = self.create_account_with_balance(
            FIRST_FAUCET_REQUEST_AMOUNT)

        self.check_value_error_if_less_than_required(sender_account,
                                                     recipient_account, amount)

        self.assert_sender_amount(sender_account.address,
                                  FIRST_FAUCET_REQUEST_AMOUNT)
        self.assert_recipient_amount(recipient_account.address,
                                     FIRST_FAUCET_REQUEST_AMOUNT)

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: send more than exist on account: spl (with different precision)"
    )
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_spl(self, amount):
        '''Send more than exist on account: spl (with different precision)'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send more than exist on account: ERC20")
    def test_send_more_than_exist_on_account_erc20(self):
        '''Send more than exist on account: ERC20'''
        pass

    @allure.step("test: send zero: neon")
    def test_zero_neon(self):
        '''Send zero: neon'''
        sender_account = self.create_account_with_balance(
            FIRST_FAUCET_REQUEST_AMOUNT)
        recipient_account = self.create_account_with_balance(
            FIRST_FAUCET_REQUEST_AMOUNT)

        self.transfer_zero_neon(sender_account, recipient_account,
                                DEFAULT_TRANSFER_AMOUNT)

        self.assert_sender_amount(sender_account.address,
                                  FIRST_FAUCET_REQUEST_AMOUNT)
        self.assert_recipient_amount(recipient_account.address,
                                     FIRST_FAUCET_REQUEST_AMOUNT)

    @pytest.mark.skip("not yet done")
    @allure.step("test: send zero: spl (with different precision)")
    def test_zero_spl(self):
        '''Send zero: spl (with different precision)'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send zero: ERC20")
    def test_zero_erc20(self):
        '''Send zero: ERC20'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send negative sum from account: neon")
    def test_send_negative_sum_from_account_neon(self):
        '''Send negative sum from account: neon'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: send negative sum from account: spl (with different precision)")
    def test_send_negative_sum_from_account_spl(self):
        '''Send negative sum from account: spl (with different precision)'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send negative sum from account: ERC20")
    def test_send_negative_sum_from_account_erc20(self):
        '''Send negative sum from account: ERC20'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send token to an invalid address")
    def test_send_token_to_an_invalid_address(self):
        '''Send token to an invalid address'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send token to a non-existing address")
    def test_send_more_token_to_non_existing_address(self):
        '''Send token to a non-existing address'''
        pass
