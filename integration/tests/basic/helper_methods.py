import allure
from eth_account import Account

from integration.tests.base import BaseTests

FIRST_FAUCET_REQUEST_AMOUNT = 5
SECOND_FAUCET_REQUEST_AMOUNT = 3


class BasicHelpers(BaseTests):
    @allure.step("creating a new account")
    def create_account(self) -> Account:
        return self.web3_client.create_account()

    @allure.step("getting balance of account")
    def get_balance(self, address: str) -> int:
        return self.web3_client.eth.get_balance(address)

    # TODO: write code
    @allure.step("requesting faucet")
    def request_faucet(self, wallet: str, amount: int):
        self.faucet.request_neon(wallet, amount=amount)

    # TODO: write code
    @allure.step("transferring tokens")
    def transfer_neon(self, sender_address: str, recipient_address: str,
                      amount: int):
        pass

    @allure.step("checking balance")
    def assert_amount(self, address: str, amount: int):
        balance = self.web3_client.fromWei(self.get_balance(address), "ether")
        assert balance == amount, f"expected balance = {amount}, actual balance = {balance}"