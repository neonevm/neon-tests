import typing as tp
from decimal import Decimal

import allure
import pytest
import web3
from eth_account import Account

from integration.tests.base import BaseTests
from integration.tests.basic.helpers.error_message import ErrorMessage
from integration.tests.basic.helpers.json_rpc_requester import JsonRpcClient
from integration.tests.basic.model.model import AccountData, JsonRpcErrorResponse, JsonRpcResponse
from integration.tests.basic.test_data.input_data import InputData

WAITING_FOR_MS = "waiting for MS"

WAITING_FOR_ERC20 = "ERC20 is in progress"
WAITIING_FOR_CONTRACT_SUPPORT = "no contracts are yet done"

DEVNET_SENDER_ADDRESS = "0x59cf149216bFBfeA66C4b1d2097d37A3Dfe74ff0"
DEVNET_SENDER_KEY = "269bc1dd17e8cbfd4280a0f58d67a0ca4631a2a8debebb88b6017083fc90c56d"


class BaseMixin(BaseTests):

    json_rpc_client: JsonRpcClient = None
    _sender_account: Account = None
    _recipient_account: Account = None

    @pytest.fixture(autouse=True)
    def prepare_env(self, json_rpc_client):
        self.json_rpc_client = json_rpc_client

    @property
    def sender_account(self):
        if not BaseMixin._sender_account:
            account = self.create_account_with_balance()
            BaseMixin._sender_account = account
        return BaseMixin._sender_account

    @property
    def recipient_account(self):
        if not BaseMixin._recipient_account:
            account = self.create_account_with_balance(is_sender=False)
            BaseMixin._recipient_account = account
        return BaseMixin._recipient_account

    @staticmethod
    def assert_expected_raises(
        response: tp.Union[JsonRpcResponse, JsonRpcErrorResponse], err_message: str = None
    ) -> None:
        """Assertions about expected exceptions"""
        with pytest.raises(AssertionError) as excinfo:
            assert isinstance(response, JsonRpcResponse), response.error.get("message")
        if err_message:
            assert err_message in str(excinfo.value)

    def create_account(self) -> Account:
        """Creates a new account"""
        return self.web3_client.create_account()

    def get_balance(self, address: str) -> Decimal:
        """Gets balance of account"""
        return self.web3_client.eth.get_balance(address)

    def request_faucet_neon(self, wallet: str, amount: int):
        """Requests faucet for Neon"""
        self.faucet.request_neon(wallet, amount=amount)

    def create_account_with_balance(
        self, amount: int = InputData.FAUCET_1ST_REQUEST_AMOUNT.value, is_sender: bool = True
    ) -> Account:
        """Creates a new account with balance"""
        account = self.create_account()
        if is_sender:
            self.request_faucet_neon(account.address, amount)
        return account

    # @allure.step("requesting faucet for ERC20")
    # def request_faucet_erc20(self, wallet: str, amount: int):
    #     self.faucet.request_sol(wallet, amount=amount)

    def process_transaction(
        self, sender_account: Account, recipient_account: Account, amount: float = 0.0
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Processes transaction"""
        with allure.step(f"Sending {amount} from {sender_account.address} to {recipient_account.address}"):
            return self.web3_client.send_neon(sender_account, recipient_account, amount)

    def process_transaction_with_failure(
        self,
        sender_account: Account,
        recipient_account: tp.Union[Account, AccountData],
        amount: int,
        error_message: str = "",
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Processes transaction, expects a failure"""
        tx: tp.Union[web3.types.TxReceipt, None] = None
        with allure.step(f"Sending {amount} from {sender_account.address} to {recipient_account.address}"):
            with pytest.raises(Exception) as error_info:
                tx = self.web3_client.send_neon(sender_account, recipient_account, amount)
            assert error_info, "Transaction failed"
            if error_message:
                assert error_message in str(error_info.value)
            return tx

    def transfer_neon(
        self, sender_account: Account, recipient_account: Account, amount: int
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Transfers tokens"""
        return self.process_transaction(sender_account, recipient_account, amount)

    def check_value_error_if_less_than_required(
        self, sender_account: Account, recipient_account: Account, amount: int
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Checks in case the balance is less than required"""
        return self.process_transaction_with_failure(
            sender_account, recipient_account, amount, ErrorMessage.EXPECTING_VALUE.value
        )

    def assert_balance(self, address: str, expected_amount: float, rnd_dig: int = None):
        """Compares balance of an account with expectation"""
        balance = float(self.web3_client.fromWei(self.get_balance(address), "ether"))
        self.check_balance(expected_amount, balance, rnd_dig=rnd_dig)

    @allure.step("deploying an ERC_20 conract")
    def deploy_contract(self):
        """Deploys an ERC-20 contract"""
        pass

    @allure.step("calculating gas")
    def calculate_trx_gas(self, tx_receipt: web3.types.TxReceipt) -> float:
        gas_used_in_tx = tx_receipt.cumulativeGasUsed * self.web3_client.fromWei(self.web3_client.gas_price(), "ether")
        return float(round(gas_used_in_tx, InputData.ROUND_DIGITS.value))

    @staticmethod
    def assert_result_object(data: JsonRpcResponse) -> bool:
        """Checks that the result sub object is present"""
        return hasattr(data, "result")

    @allure.step("calculating gas")
    def calculate_trx_gas(self, tx_receipt: web3.types.TxReceipt) -> float:
        gas_used_in_tx = tx_receipt.cumulativeGasUsed * self.web3_client.fromWei(self.web3_client.gas_price(), "ether")
        return float(round(gas_used_in_tx, InputData.ROUND_DIGITS.value))

    @staticmethod
    def assert_no_error_object(data: JsonRpcErrorResponse) -> bool:
        """Checks that the error sub object is not present"""
        return not hasattr(data, "error")

    @staticmethod
    def assert_is_successful_response(actual_result: tp.Union[JsonRpcResponse, JsonRpcErrorResponse]) -> bool:
        return isinstance(actual_result, JsonRpcResponse)

    @staticmethod
    def check_balance(expected: float, actual: Decimal, rnd_dig: int = InputData.ROUND_DIGITS.value):
        """Compares the balance with expectation"""
        expected_dec = round(expected, rnd_dig)
        actual_dec = round(actual, rnd_dig)

        assert actual_dec == expected_dec, f"expected balance = {expected_dec}, actual balance = {actual_dec}"
