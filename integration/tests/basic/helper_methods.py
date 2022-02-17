import allure
import allure_commons
from eth_account import Account


@allure_commons.story("Basic")
class TestBasic(BaseTests):
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
        balance = self.get_balance(address)
        assert balance == amount