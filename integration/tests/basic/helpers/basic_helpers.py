import allure
import pytest
import web3
from _pytest.config import Config
from eth_account import Account
from typing import Optional, Union
from integration.tests.base import BaseTests
from integration.tests.basic.helpers.json_rpc_requester import JsonRpcRequester
from integration.tests.basic.model.json_rpc_error_response import JsonRpcErrorResponse
from integration.tests.basic.model.json_rpc_response import JsonRpcResponse

FIRST_FAUCET_REQUEST_AMOUNT = 5
SECOND_FAUCET_REQUEST_AMOUNT = 3
FIRST_AMOUNT_IN_RESPONSE = '0x4563918244f40000'
GREAT_AMOUNT = 1_000
DEFAULT_TRANSFER_AMOUNT = 3

WAITING_FOR_MS = "waiting for MS"
# TODO: remove it later
WAITING_FOR_ERC20 = "ERC20 is in progress"
WAITING_FOR_TRX = "Json-RPC not yet done"
WAITIING_FOR_CONTRACT_SUPPORT = "no contracts are yet done"
NOT_YET_DONE = "not yet done"


class BasicHelpers(BaseTests):
    jsonrpc_requester: JsonRpcRequester

    @pytest.fixture(autouse=True)
    def prepare_json_rpc_requester(self, jsonrpc_requester: JsonRpcRequester):
        self.jsonrpc_requester = jsonrpc_requester

    @allure.step("creating a new account")
    def create_account(self) -> Account:
        '''Creates a new account'''
        return self.web3_client.create_account()

    @allure.step("getting balance of account")
    def get_balance(self, address: str) -> int:
        '''Gets balance of account'''
        return self.web3_client.eth.get_balance(address)

    @allure.step("requesting faucet for Neon")
    def request_faucet_neon(self, wallet: str, amount: int):
        '''Requests faucet for Neon'''
        self.faucet.request_neon(wallet, amount=amount)

    @allure.step("creating a new account with balance")
    def create_account_with_balance(self, amount: int) -> Account:
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
    def process_transaction(
            self,
            sender_account: Account,
            recipient_account: Account,
            amount: int,
            message: str = "") -> Union[web3.types.TxReceipt, None]:
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
            message: str = "") -> Union[web3.types.TxReceipt, None]:
        '''Processes transaction, expects a failure'''

        tx: Union[web3.types.TxReceipt, None] = None
        with pytest.raises(Exception) as error_info:
            tx = self.web3_client.send_neon(sender_account, recipient_account,
                                            amount)

        if error_info != None:
            if message:
                assert message in str(error_info)
            assert None != error_info, "Transaction failed"

        return tx

    @allure.step("transferring tokens")
    def transfer_neon(self, sender_account: Account,
                      recipient_account: Account,
                      amount: int) -> Union[web3.types.TxReceipt, None]:
        '''Transers tokens'''
        return self.process_transaction(sender_account, recipient_account,
                                        amount, "InvalidInstructionData")

    @allure.step("transferring 0 tokens")
    def transfer_zero_neon(self, sender_account: Account,
                           recipient_account: Account,
                           amount: int) -> Union[web3.types.TxReceipt, None]:
        '''Transfers 0 tokens'''
        return self.process_transaction(sender_account, recipient_account,
                                        amount, "aaa")

    @allure.step("transferring tokens to an invalid address")
    def transfer_to_invalid_address(
            self, sender_account: Account, recipient_account: Account,
            amount: int, message: str) -> Union[web3.types.TxReceipt, None]:
        '''Transfers tokens to an invalid address'''
        return self.process_transaction_with_failure(sender_account,
                                                     recipient_account, amount,
                                                     message)

    @allure.step("checking in case the balance is less than required")
    def check_value_error_if_less_than_required(
            self, sender_account: Account, recipient_account: Account,
            amount: int) -> Union[web3.types.TxReceipt, None]:
        '''Checks in case the balance is less than required'''
        return self.process_transaction_with_failure(sender_account,
                                                     recipient_account, amount,
                                                     "Resulting wei value")

    @allure.step("comparing the balance with expectation")
    def compare_balance(self, expected: int, actual: int, message: str):
        '''Compares the balance with expectation'''
        assert actual == expected, message + f"expected balance = {expected}, actual balance = {actual}"

    @allure.step("comparing balance of an account with expectation")
    def assert_amount(self,
                      address: str,
                      expected_amount: int,
                      message: str = ""):
        '''Compares balance of an account with expectation'''
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(expected_amount, balance, message)

    @allure.step("checking sender's balance")
    def assert_sender_amount(self, address: str, expected_amount: int):
        '''Checks sender's balance'''
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(expected_amount, balance, "Sender: ")

    @allure.step("checking recipient's balance")
    def assert_recipient_amount(self, address: str, expected_amount: int):
        '''Checks recipient's balance'''
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(expected_amount, balance, "Recipient: ")

    @allure.step("checking that the result subobject is present")
    def assert_result_object(self, data: JsonRpcResponse) -> bool:
        '''Checks that the result subobject is present'''
        try:
            return data.result != None
        except Exception:
            return False

    @allure.step("checking that the error subobject is not present")
    def assert_no_error_object(self, data: JsonRpcErrorResponse) -> bool:
        '''Checks that the error subobject is not present'''
        try:
            return data.error == None
        except Exception:
            return True