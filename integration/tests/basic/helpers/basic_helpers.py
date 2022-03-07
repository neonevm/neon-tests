import allure
import pytest
import web3
from _pytest.config import Config
from eth_account import Account
from typing import Optional, Union
from integration.tests.base import BaseTests
from integration.tests.basic.helpers.json_rpc_requester import JsonRpcRequester

FIRST_FAUCET_REQUEST_AMOUNT = 5
SECOND_FAUCET_REQUEST_AMOUNT = 3
FIRST_AMOUNT_IN_RESPONSE = '0x4563918244f40000'
GREAT_AMOUNT = 1_000
DEFAULT_TRANSFER_AMOUNT = 3

WAITING_FOR_MS = "waiting for MS"


@pytest.fixture(scope="class")
def prepare_account():  # faucet, web3_client):
    # """Create new account for tests and save operator pre/post balances"""
    # start_neon_balance = operator.get_neon_balance()
    # start_sol_balance = operator.get_solana_balance()
    # with allure.step(f"Operator initial balance: {start_neon_balance / LAMPORT_PER_SOL} NEON {start_sol_balance / LAMPORT_PER_SOL} SOL"):
    #     pass
    # with allure.step("Create account for tests"):
    #     acc = web3_client.eth.account.create()
    # with allure.step(f"Request 100 NEON from faucet for {acc.address}"):
    #     faucet.request_neon(acc.address, 100)
    #     assert web3_client.get_balance(acc) == 100
    # yield acc
    # end_neon_balance = operator.get_neon_balance()
    # end_sol_balance = operator.get_solana_balance()
    # with allure.step(f"Operator end balance: {end_neon_balance / LAMPORT_PER_SOL} NEON {end_sol_balance / LAMPORT_PER_SOL} SOL"):
    #     pass

    yield


class BasicHelpers(BaseTests):
    jsonrpc_requester: JsonRpcRequester

    @pytest.fixture(autouse=True)
    def prepare_json_rpc_requester(self, jsonrpc_requester: JsonRpcRequester):
        self.jsonrpc_requester = jsonrpc_requester

    @allure.step("creating a new account")
    def create_account(self) -> Account:
        return self.web3_client.create_account()

    @allure.step("getting balance of account")
    def get_balance(self, address: str) -> int:
        return self.web3_client.eth.get_balance(address)

    @allure.step("requesting faucet for Neon")
    def request_faucet_neon(self, wallet: str, amount: int):
        self.faucet.request_neon(wallet, amount=amount)

    @allure.step("creating a new account with balance")
    def create_account_with_balance(self, amount: int) -> Account:
        account = self.create_account()
        self.request_faucet_neon(account.address, amount)
        return account

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

        tx = self.web3_client.send_neon(sender_account, recipient_account,
                                        amount)

        # TODO: remove
        print("--------------------------------------")
        print(tx)
        #

        return tx

    @allure.step("processing transaction, expecting a failure")
    def process_transaction_with_failure(
            self,
            sender_account: Account,
            recipient_account: Account,
            amount: int,
            message: str = "") -> Union[web3.types.TxReceipt, None]:

        tx: Union[web3.types.TxReceipt, None] = None
        with pytest.raises(Exception) as error_info:
            tx = self.web3_client.send_neon(sender_account, recipient_account,
                                            amount)

        # TODO: remove
        print(error_info)
        #

        if error_info != None:
            if message:
                assert message in str(error_info)
            assert None != error_info, "Transaction failed"

        # TODO: remove
        print("--------------------------------------")
        print(tx)
        #

        return tx

    @allure.step("transferring tokens")
    def transfer_neon(self, sender_account: Account,
                      recipient_account: Account,
                      amount: int) -> Union[web3.types.TxReceipt, None]:
        return self.process_transaction(sender_account, recipient_account,
                                        amount, "InvalidInstructionData")

    @allure.step("transferring 0 tokens")
    def transfer_zero_neon(self, sender_account: Account,
                           recipient_account: Account,
                           amount: int) -> Union[web3.types.TxReceipt, None]:
        return self.process_transaction(sender_account, recipient_account,
                                        amount, "aaa")

    @allure.step("transferring to an invalid address")
    def transfer_to_invalid_address(
            self, sender_account: Account, recipient_account: Account,
            amount: int, message: str) -> Union[web3.types.TxReceipt, None]:
        return self.process_transaction_with_failure(sender_account,
                                                     recipient_account, amount,
                                                     message)

    @allure.step("checking less than required")
    def check_value_error_if_less_than_required(
            self, sender_account: Account, recipient_account: Account,
            amount: int) -> Union[web3.types.TxReceipt, None]:
        return self.process_transaction_with_failure(sender_account,
                                                     recipient_account, amount,
                                                     "Resulting wei value")

    def compare_balance(self, expected: int, actual: int, message: str):
        assert actual == expected, message + f"expected balance = {expected}, actual balance = {actual}"

    def assert_amount(self,
                      address: str,
                      expected_amount: int,
                      message: str = ""):
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(expected_amount, balance, message)

    @allure.step("checking sender balance")
    def assert_sender_amount(self, address: str, expected_amount: int):
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(expected_amount, balance, "Sender: ")

    @allure.step("checking recipient balance")
    def assert_recipient_amount(self, address: str, expected_amount: int):
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(expected_amount, balance, "Recipient: ")