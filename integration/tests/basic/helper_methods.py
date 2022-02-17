import allure
import pytest
from eth_account import Account
import web3

from integration.tests.base import BaseTests

FIRST_FAUCET_REQUEST_AMOUNT = 5
SECOND_FAUCET_REQUEST_AMOUNT = 3
GREAT_AMOUNT = 1_000
DEFAULT_TRANSFER_AMOUNT = 3


class BasicHelpers(BaseTests):
    @allure.step("creating a new account")
    def create_account(self) -> Account:
        return self.web3_client.create_account()

    @allure.step("getting balance of account")
    def get_balance(self, address: str) -> int:
        return self.web3_client.eth.get_balance(address)

    @allure.step("requesting faucet for Neon")
    def request_faucet_neon(self, wallet: str, amount: int):
        self.faucet.request_neon(wallet, amount=amount)

    # @allure.step("requesting faucet for ERC20")
    # def request_faucet_erc20(self, wallet: str, amount: int):
    #     self.faucet.request_sol(wallet, amount=amount)

    @allure.step("transferring tokens")
    def transfer_neon(self, sender_account: Account, recipient_account: Account,
                      amount: int, gas: int, gas_price:int) -> web3.types.TxReceipt:
        self.web3_client.send_neon(sender_account, recipient_account,   amount=amount,gas=gas,gas_price=gas_price)
    
    @allure.step("checking less than required")
    def check_value_error_if_less_than_required(self, sender_account: Account, recipient_account: Account, amount: int, gas: int, gas_price:int);
        with pytest.raises(ValueError) as error_info:
            self.transfer_neon(sender_account,recipient_account,amount)
        assert "The account balance is less than required" in str(error_info.value)

    @allure.step("comparing expected and actual balance")
    def compare_balance(self, expected: int, actual: int):
        assert actual == expected, f"expected balance = {expected}, actual balance = {actual}"

    @allure.step("checking balance")
    def assert_amount(self, address: str, expected_amount: int):
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        self.compare_balance(expected_amount, balance)
