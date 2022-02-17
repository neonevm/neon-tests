import allure
import pytest
from integration.tests.basic.helper_methods import DEFAULT_TRANSFER_AMOUNT, FIRST_FAUCET_REQUEST_AMOUNT, GREAT_AMOUNT, BasicHelpers

TRANSFER_AMOUNT_DATA = [(10), (100), (10.1)]


@allure.story("Basic: transfer tests")
class TestTransfer(BasicHelpers):
    @allure.step("test: send neon from one account to another")
    def test_send_neon_from_one_account_to_another(self):
        '''Send neon from one account to another'''
        sender_account = self.create_account()
        self.request_faucet_neon(sender_account.address, GREAT_AMOUNT)
        self.assert_amount(sender_account.address, GREAT_AMOUNT)

        recipient_account = self.create_account()
        self.request_faucet_neon(recipient_account.address,
                            FIRST_FAUCET_REQUEST_AMOUNT)
        self.assert_amount(recipient_account.address,
                           FIRST_FAUCET_REQUEST_AMOUNT)

        tx_receipt = self.web3_client.send_neon(sender_account.address,
                                                recipient_account.address,
                                                2.5, # DEFAULT_TRANSFER_AMOUNT,
                                                gas=10_000,
                                                gas_price=1_000_000_000)

        self.assert_amount(sender_account.address,
                           GREAT_AMOUNT - DEFAULT_TRANSFER_AMOUNT)
        self.assert_amount(
            recipient_account.address,
            FIRST_FAUCET_REQUEST_AMOUNT + DEFAULT_TRANSFER_AMOUNT)

    # @pytest.mark.skip("not yet done")
    # @allure.step("test: send spl wrapped account from one account to another")
    # def test_send_spl_wrapped_account_from_one_account_to_another(self):
    #     '''Send spl wrapped account from one account to another'''
    #     pass

    @allure.step("test: send more than exist on account: neon")
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_neon(self, amount):
        '''Send more than exist on account: neon'''
        sender_account = self.create_account()
        self.request_faucet_neon(sender_account.address,
                            FIRST_FAUCET_REQUEST_AMOUNT)
        self.assert_amount(sender_account.address, FIRST_FAUCET_REQUEST_AMOUNT)

        recipient_account = self.create_account()
        self.request_faucet_neon(recipient_account.address,
                            FIRST_FAUCET_REQUEST_AMOUNT)
        self.assert_amount(recipient_account.address,
                           FIRST_FAUCET_REQUEST_AMOUNT)

        with pytest.raises(ValueError):
            tx_receipt = self.web3_client.send_neon(sender_account,
                                                    recipient_account,
                                                    amount=amount)

        self.assert_amount(sender_account.address,
                           FIRST_FAUCET_REQUEST_AMOUNT - amount)
        self.assert_amount(recipient_account.address,
                           FIRST_FAUCET_REQUEST_AMOUNT + amount)

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: send more than exist on account: spl (with different precision)"
    )
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_spl(self, amount):
        '''Send more than exist on account: spl (with different precision)'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send more than exist on account: ERC20")
    def test_send_more_than_exist_on_account_erc20(self):
        '''Send more than exist on account: ERC20'''
        pass

    @allure.step("test: send zero: neon")
    def test_send_more_than_exist_on_account_neon(self):
        '''Send zero: neon'''
        sender_account = self.create_account()
        self.request_faucet_neon(sender_account.address, GREAT_AMOUNT)
        self.assert_amount(sender_account.address, GREAT_AMOUNT)

        recipient_account = self.create_account()
        self.request_faucet_neon(recipient_account.address,
                            FIRST_FAUCET_REQUEST_AMOUNT)
        self.assert_amount(recipient_account.address,
                           FIRST_FAUCET_REQUEST_AMOUNT)

        tx_receipt = self.web3_client.send_neon(sender_account,
                                                recipient_account, 0)

        self.assert_amount(sender_account.address,
                           GREAT_AMOUNT)
        self.assert_amount(
            recipient_account.address,
            FIRST_FAUCET_REQUEST_AMOUNT)

    @pytest.mark.skip("not yet done")
    @allure.step("test: send zero: spl (with different precision)")
    def test_send_more_than_exist_on_account_spl(self):
        '''Send zero: spl (with different precision)'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send zero: ERC20")
    def test_send_more_than_exist_on_account_erc20(self):
        '''Send zero: ERC20'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send negative sum from account: neon")
    def test_send_more_than_exist_on_account_neon(self):
        '''Send negative sum from account: neon'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: send negative sum from account: spl (with different precision)")
    def test_send_more_than_exist_on_account_spl(self):
        '''Send negative sum from account: spl (with different precision)'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send negative sum from account: ERC20")
    def test_send_more_than_exist_on_account_erc20(self):
        '''Send negative sum from account: ERC20'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send token to an invalid addres")
    def test_send_more_than_exist_on_account_spl(self):
        '''Send token to an invalid address'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send token to a non-existing address")
    def test_send_more_than_exist_on_account_spl(self):
        '''Send token to a non-existing address'''
        pass
