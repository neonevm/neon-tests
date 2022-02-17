import allure
import pytest
from integration.tests.basic.helper_methods import TestBasic


@allure.story("Basic: transfer tests")
class TestTransfer(TestBasic):
    @pytest.mark.skip("not yet done")
    @allure.step("test: send neon from one account to another")
    def test_send_neon_from_one_account_to_another(self):
        '''Send neon from one account to another'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send spl wrapped account from one account to another")
    def test_send_spl_wrapped_account_from_one_account_to_another(self):
        '''Send spl wrapped account from one account to another'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send more than exist on account: neon")
    def test_send_more_than_exist_on_account_neon(self):
        '''Send more than exist on account: neon'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: send more than exist on account: spl (with different precision)"
    )
    def test_send_more_than_exist_on_account_spl(self):
        '''Send more than exist on account: spl (with different precision)'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send more than exist on account: ERC20")
    def test_send_more_than_exist_on_account_erc20(self):
        '''Send more than exist on account: ERC20'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send zero: neon")
    def test_send_more_than_exist_on_account_neon(self):
        '''Send zero: neon'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send zero: spl (with different precision)")
    def test_send_more_than_exist_on_account_spl(self):
        '''Send zero: spl (with different precision)'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send zero: ERC20")
    def test_send_more_than_exist_on_account_erc20(self):
        '''Send zero: ERC20'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send negative sum from account: neon")
    def test_send_more_than_exist_on_account_neon(self):
        '''Send negative sum from account: neon'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: send negative sum from account: spl (with different precision)")
    def test_send_more_than_exist_on_account_spl(self):
        '''Send negative sum from account: spl (with different precision)'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send negative sum from account: ERC20")
    def test_send_more_than_exist_on_account_erc20(self):
        '''Send negative sum from account: ERC20'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send token to an invalid addres")
    def test_send_more_than_exist_on_account_spl(self):
        '''Send token to an invalid address'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: send token to a non-existing address")
    def test_send_more_than_exist_on_account_spl(self):
        '''Send token to a non-existing address'''
        # request faucet
        # check balance
        # request faucet
        # check balance
        # send tokens
        # check balance
        # check balance
        pass
