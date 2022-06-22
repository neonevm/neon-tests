import time
import typing as tp
from dataclasses import dataclass
from decimal import Decimal

import allure
import pytest
import web3
import eth_account.signers.local

from utils.consts import Unit, InputTestConstants
from utils.helpers import gen_hash_of_block
from utils.apiclient import JsonRPCSession
from integration.tests.base import BaseTests
from integration.tests.basic.helpers.assert_message import ErrorMessage


@dataclass
class AccountData:
    address: str
    key: str = ""


class BaseMixin(BaseTests):

    json_rpc_client: JsonRPCSession = None
    _sender_account: eth_account.signers.local.LocalAccount = None
    _recipient_account: eth_account.signers.local.LocalAccount = None
    _invalid_account: AccountData = None

    @pytest.fixture(autouse=True)
    def prepare_env(self, json_rpc_client):
        self.json_rpc_client = json_rpc_client

    # TODO: Fix nonce to small error and remove it
    @pytest.fixture(autouse=True)
    def wait(self):
        """Wait for nonce updated"""
        time.sleep(3)

    @property
    def sender_account(self):
        if not BaseMixin._sender_account:
            account = self.create_account_with_balance()
            BaseMixin._sender_account = account
        return BaseMixin._sender_account

    @property
    def recipient_account(self):
        if not BaseMixin._recipient_account:
            account = self.create_account_with_balance()
            BaseMixin._recipient_account = account
        return BaseMixin._recipient_account

    @property
    def invalid_account(self):
        if not BaseMixin._recipient_account:
            account = self.create_invalid_account()
            BaseMixin._invalid_account = account
        return BaseMixin._invalid_account

    @property
    def sender_account_balance(self):
        return self.get_balance_from_wei(self.sender_account.address)

    @property
    def recipient_account_balance(self):
        return self.get_balance_from_wei(self.recipient_account.address)

    @pytest.fixture(autouse=True)
    def prepare_account(self):
        """Prevents calling to a fixture with the same name from operators' tests"""
        pass

    @staticmethod
    def assert_expected_raises(
        response, err_message: str = None
    ) -> None:
        """Assertions about expected exceptions"""
        with pytest.raises(AssertionError) as excinfo:
            assert isinstance(response, JsonRpcResponse), response.error.get("message")
        if err_message:
            assert err_message in str(excinfo.value)

    def create_account(self):
        """Creates a new account"""
        return self.web3_client.create_account()

    def get_balance(self, address: str) -> Decimal:
        """Gets balance of account"""
        return self.web3_client.eth.get_balance(address)

    def get_balance_from_wei(self, address: str) -> float:
        """Gets balance from Wei"""
        return float(self.web3_client.fromWei(self.get_balance(address), Unit.ETHER))

    def request_faucet_neon(self, wallet: str, amount: int):
        """Requests faucet for Neon"""
        self.faucet.request_neon(wallet, amount=amount)

    def create_account_with_balance(
        self, amount: int = InputTestConstants.FAUCET_1ST_REQUEST_AMOUNT.value
    ):
        """Creates a new account with balance"""
        account = self.create_account()
        self.request_faucet_neon(account.address, amount)
        return account

    @staticmethod
    def create_invalid_account() -> AccountData:
        """Create non existing account"""
        return AccountData(address=gen_hash_of_block(20))

    def send_neon(
        self,
        sender_account: eth_account.signers.local.LocalAccount,
        recipient_account: eth_account.signers.local.LocalAccount,
        amount: float = 0.0,
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Processes transaction"""
        with allure.step(f"Sending {amount} from {sender_account.address} to {recipient_account.address}"):
            return self.web3_client.send_neon(sender_account, recipient_account, amount)

    def send_neon_with_failure(
        self,
        sender_account: eth_account.signers.local.LocalAccount,
        recipient_account: tp.Union[eth_account.signers.local.LocalAccount, AccountData],
        amount: tp.Union[int, float, Decimal],
        gas: tp.Optional[int] = 0,
        gas_price: tp.Optional[int] = None,
        error_message: str = None,
        exception: tp.Any = None,
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Processes transaction, expects a failure"""
        tx: tp.Union[web3.types.TxReceipt, None] = None
        exception = exception or Exception
        with allure.step(f"Sending {amount} from {sender_account.address} to {recipient_account.address}"):
            with pytest.raises(exception, match=error_message):
                tx = self.web3_client.send_neon(sender_account, recipient_account, amount, gas, gas_price)
            return tx

    def check_value_error_if_less_than_required(
        self, sender_account: eth_account.signers.local.LocalAccount,
            recipient_account: eth_account.signers.local.LocalAccount, amount: int
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Checks in case the balance is less than required"""
        return self.send_neon_with_failure(
            sender_account=sender_account,
            recipient_account=recipient_account,
            amount=amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value,
        )

    def assert_balance(self, address: str, expected_amount: float, rnd_dig: int = None):
        """Compares balance of an account with expectation"""
        balance = self.get_balance_from_wei(address)
        self.check_balance(expected_amount, balance, rnd_dig=rnd_dig)

    def assert_balance_less(
        self,
        address: str,
        calculated_balance: float,
    ):
        """Compares balance of an account, balance must be less than init balance"""
        balance = self.get_balance_from_wei(address)
        assert round(balance) <= round(
            calculated_balance
        ), f"Balance after transferring {balance} must be less or equal {calculated_balance}"

    @allure.step("calculating gas")
    def calculate_trx_gas(self, tx_receipt: web3.types.TxReceipt) -> float:
        gas_used_in_tx = tx_receipt.cumulativeGasUsed * self.web3_client.fromWei(
            self.web3_client.gas_price(), Unit.ETHER
        )
        return float(round(gas_used_in_tx, InputTestConstants.ROUND_DIGITS.value))

    @allure.step("calculating gas")
    def calculate_trx_gas(self, tx_receipt: web3.types.TxReceipt) -> float:
        gas_used_in_tx = tx_receipt.cumulativeGasUsed * self.web3_client.fromWei(
            self.web3_client.gas_price(), Unit.ETHER
        )
        return float(round(gas_used_in_tx, InputTestConstants.ROUND_DIGITS.value))

    @staticmethod
    def assert_no_error_object(data) -> bool:
        """Checks that the error sub object is not present"""
        return not hasattr(data, "error")

    @staticmethod
    def check_balance(expected: float, actual: float, rnd_dig: int = InputTestConstants.ROUND_DIGITS.value):
        """Compares the balance with expectation"""
        expected_dec = round(expected, rnd_dig)
        actual_dec = round(actual, rnd_dig)

        assert actual_dec == expected_dec, f"expected balance = {expected_dec}, actual balance = {actual_dec}"
