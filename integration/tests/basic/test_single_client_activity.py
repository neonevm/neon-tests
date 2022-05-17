import allure
import pytest
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.unit import Unit
from integration.tests.basic.test_data.input_data import InputData
from integration.tests.basic.test_transfers import DEFAULT_ERC20_BALANCE


FAUCET_TEST_DATA = [(1), (10_001)]
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

    @pytest.mark.only_stands
    @pytest.mark.parametrize("amount", FAUCET_TEST_DATA)
    def test_verify_faucet_work_single_request(self, amount: int):
        """Verify faucet work (request drop for several accounts): single request"""
        for _ in range(10):
            account = self.create_account()
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, amount)
            self.assert_balance(account.address, amount)

    @pytest.mark.only_stands
    @pytest.mark.parametrize("amount", FAUCET_TEST_DATA)
    def test_verify_faucet_work_multiple_requests(self, amount: int):
        """Verify faucet work (request drop for several accounts): double request"""
        for _ in range(10):
            account = self.create_account()
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, amount)
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, InputData.FAUCET_2ND_REQUEST_AMOUNT.value)
            self.assert_balance(account.address, amount + InputData.FAUCET_2ND_REQUEST_AMOUNT.value)
