import allure
from busypie import ONE_SECOND, wait_at_most
from busypie.durations import TWO_SECONDS
import pytest
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.unit import Unit
from integration.tests.basic.test_data.input_data import InputData
from integration.tests.basic.test_transfers import DEFAULT_ERC20_BALANCE


FAUCET_REQUEST_MESSAGE = "requesting faucet for Neon"


@allure.story("Basic: single user tests")
class TestSingleClient(BaseMixin):
    @pytest.mark.only_stands
    def test_create_account_and_get_balance(self):
        """Create account and get balance"""
        account = self.create_account()
        self.assert_balance(account.address, 0)

    @pytest.mark.only_stands
    def test_check_tokens_in_wallet_neon(self):
        """Check tokens in wallet: neon"""
        account = self.create_account()
        with allure.step(FAUCET_REQUEST_MESSAGE):
            self.request_faucet_neon(account.address, InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(account.address, InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    @pytest.mark.parametrize("amount", [(1), (10_001)])
    def test_verify_faucet_work_single_request(self, amount: int):
        """Verify faucet work (request drop for several accounts): single request"""
        for _ in range(3):
            account = self.create_account()
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, amount)
            wait_at_most(TWO_SECONDS).poll_delay(TWO_SECONDS).until(lambda: True)
            self.assert_balance(account.address, amount)

    def test_verify_faucet_work_multiple_requests(self):
        """Verify faucet work (request drop for several accounts): double request"""
        initial_amount = InputData.FAUCET_1ST_REQUEST_AMOUNT.value
        for _ in range(3):
            account = self.create_account()
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, initial_amount)
            wait_at_most(ONE_SECOND).poll_delay(ONE_SECOND).until(lambda: True)
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, InputData.FAUCET_2ND_REQUEST_AMOUNT.value)
            wait_at_most(TWO_SECONDS).poll_delay(TWO_SECONDS).until(lambda: True)
            self.assert_balance(account.address, initial_amount + InputData.FAUCET_2ND_REQUEST_AMOUNT.value)
