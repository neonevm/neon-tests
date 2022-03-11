from decimal import Decimal
import allure
import pytest
import web3
from _pytest.config import Config
from eth_account import Account
from typing import Optional, Union
from integration.tests.base import BaseTests
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.error_message import ErrorMessage
from integration.tests.basic.helpers.json_rpc_requester import JsonRpcRequester
from integration.tests.basic.model.model import JsonRpcErrorResponse, JsonRpcResponse
from integration.tests.basic.test_data.input_data import InputData

WAITING_FOR_MS = "waiting for MS"
# TODO: remove it after t
WAITING_FOR_ERC20 = "ERC20 is in progress"
WAITIING_FOR_CONTRACT_SUPPORT = "no contracts are yet done"


class BasicTests(BaseTests):
    jsonrpc_requester: JsonRpcRequester
    sender_account: Account
    recipient_account: Account

    @pytest.fixture(autouse=True)
    def prepare_json_rpc_requester(self, jsonrpc_requester: JsonRpcRequester):
        self.jsonrpc_requester = jsonrpc_requester

    @pytest.fixture
    def prepare_accounts(self):
        self.sender_account = self.create_account_with_balance()
        self.recipient_account = self.create_account_with_balance()
        yield

    @allure.step("creating a new account")
    def create_account(self) -> Account:
        '''Creates a new account'''
        return self.web3_client.create_account()

    def get_balance(self, address: str) -> Decimal:
        '''Gets balance of account'''
        return self.web3_client.eth.get_balance(address)

    @allure.step("requesting faucet for Neon")
    def request_faucet_neon(self, wallet: str, amount: int):
        '''Requests faucet for Neon'''
        self.faucet.request_neon(wallet, amount=amount)

    @allure.step("creating a new account with balance")
    def create_account_with_balance(
            self,
            amount: int = InputData.FAUCET_1ST_REQUEST_AMOUNT.value
    ) -> Account:
        '''Creates a new account with balance'''
        account = self.create_account()
        self.request_faucet_neon(account.address, amount)
        return account

    @allure.step("deploying an ERC_20 conract")
    def deploy_contract(self):
        '''Deploys an ERC-20 contract'''
        pass

    # @allure.step("requesting faucet for ERC20")
    # def request_faucet_erc20(self, wallet: str, amount: int):
    #     self.faucet.request_sol(wallet, amount=amount)

    @allure.step("processing transaction")
    def process_transaction(self, sender_account: Account,
                            recipient_account: Account,
                            amount: int) -> Union[web3.types.TxReceipt, None]:
        '''Processes transaction'''

        tx = self.web3_client.send_neon(sender_account, recipient_account,
                                        amount)

        return tx

    @allure.step("processing transaction, expecting a failure")
    def process_transaction_with_failure(
            self,
            sender_account: Account,
            recipient_account: Account,
            amount: int,
            error_message: str = "") -> Union[web3.types.TxReceipt, None]:
        '''Processes transaction, expects a failure'''

        tx: Union[web3.types.TxReceipt, None] = None
        with pytest.raises(Exception) as error_info:
            tx = self.web3_client.send_neon(sender_account, recipient_account,
                                            amount)

        if error_info != None:

            if error_message:
                assert error_message in str(error_info)
            assert None != error_info, "Transaction failed"

        return tx

    def transfer_neon(self, sender_account: Account,
                      recipient_account: Account,
                      amount: int) -> Union[web3.types.TxReceipt, None]:
        '''Transers tokens'''
        return self.process_transaction(sender_account, recipient_account,
                                        amount)

    def transfer_zero_neon(self, sender_account: Account,
                           recipient_account: Account,
                           amount: int) -> Union[web3.types.TxReceipt, None]:
        '''Transfers 0 tokens'''
        return self.process_transaction(sender_account, recipient_account,
                                        amount)

    def transfer_negative_neon(
            self, sender_account: Account, recipient_account: Account,
            amount: int) -> Union[web3.types.TxReceipt, None]:
        '''Transfers negative amount of tokens'''
        return self.process_transaction_with_failure(
            sender_account, recipient_account, amount,
            ErrorMessage.NEGATIVE_VALUE.value)

    def transfer_to_invalid_address(
            self, sender_account: Account, recipient_account: Account,
            amount: int, message: str) -> Union[web3.types.TxReceipt, None]:
        '''Transfers tokens to an invalid address'''
        return self.process_transaction_with_failure(sender_account,
                                                     recipient_account, amount,
                                                     message)

    def check_value_error_if_less_than_required(
            self, sender_account: Account, recipient_account: Account,
            amount: int) -> Union[web3.types.TxReceipt, None]:
        '''Checks in case the balance is less than required'''
        return self.process_transaction_with_failure(
            sender_account, recipient_account, amount,
            ErrorMessage.EXPECTING_VALUE.value)

    @allure.step("comparing the balance with expectation")
    def compare_balance(self, expected: float, actual: Decimal, message: str):
        '''Compares the balance with expectation'''
        expected_dec = round(expected, InputData.ROUND_DIGITS.value)
        actual_dec = float(round(actual, InputData.ROUND_DIGITS.value))

        assert actual_dec == expected_dec, message + f"expected balance = {expected_dec}, actual balance = {actual_dec}"

    @allure.step("comparing balance of an account with expectation")
    def assert_amount(self,
                      address: str,
                      expected_amount: float,
                      message: str = ""):
        '''Compares balance of an account with expectation'''
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(expected_amount, balance, message)

    @allure.step("checking sender's balance")
    def assert_sender_amount(self, address: str, expected_amount: float):
        '''Checks sender's balance'''
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(
            expected_amount, balance,
            f"Sender: expected ={expected_amount}, actual = {balance}")

    @allure.step("checking recipient's balance")
    def assert_recipient_amount(self, address: str, expected_amount: float):
        '''Checks recipient's balance'''
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(
            expected_amount, balance,
            f"Recipient: expected ={expected_amount}, actual = {balance}")

    def assert_result_object(self, data: JsonRpcResponse) -> bool:
        '''Checks that the result subobject is present'''
        try:
            return data.result != None
        except Exception:
            return False

    def assert_no_error_object(self, data: JsonRpcErrorResponse) -> bool:
        '''Checks that the error subobject is not present'''
        try:
            return data.error == None
        except Exception:
            return True

    def assert_is_successful_response(
            self, actual_result: Union[JsonRpcResponse,
                                       JsonRpcErrorResponse]) -> bool:
        return isinstance(actual_result, JsonRpcResponse)

    @allure.step("calculating gas")
    def calculate_trx_gas(self, tx_receipt: web3.types.TxReceipt) -> Decimal:
        return tx_receipt.cumulativeGasUsed * self.web3_client.gas_price(
        ) * 0.000_000_000_000_000_001
