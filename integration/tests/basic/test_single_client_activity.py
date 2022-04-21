import allure
import pytest

from integration.tests.basic.helpers.basic import WAITING_FOR_ERC20, WAITING_FOR_MS, BaseMixin
from integration.tests.basic.test_data.input_data import InputData

"""
1.	Create account and get balance
2.	Check tokens in wallet
	 - neon
	 - spl
	 - erc20
3.	Send neon from one account to another
4.	Send erc20 token from one account to another
5.	Send spl wrapped account from one account to another
6.	Send more than exist on account
	 - neon
	 - spl (with different precision)
	 - erc20
7.	Send zero
	 - neon
	 - spl
	 - erc20
8.	Send negative sum from account
	 - neon
	 - spl
	 - erc20
9.	Verify faucet work (request drop for several accounts)
	 - single request
	 - double request
# 10.	Interact with simple contract
# 11.	Deploy erc20 contract with tokens and mint this token
# 12.	Verify implemented rpc calls work
# 13.	Speed up transaction by increase gas
# 14.	Cancel transaction when gasprice setted very small for tx
15.	Send token to an invalid address
16.	Send token to a non-existing address
# 17.	Move tokens from solana to neon
# 18.	Move tokens from neon to solana
# 19.	Create TX like NeonSwap (thus leveraging airdropper) and swap token
# 20.	Check ERC-1820 transaction (without chain_id in sign)
# 21.	Generate bad sign (when v, r, s over allowed size)

Есть много известных вариантов, описать все не очень реалистично.
Самые простые:
Слишком маленький gas_limit
Слишком большой gas_limit > u64::max
Слишком большой gas_price > u64::max
Слишком большой gas_limit * gas_price > u64::max
Недостаточно неонов на оплату газа
Недостаточно неонов на трансфер
Размер эфировской транзакции больше лимита, лимит точно не известен, 256кб точно больше
Размер солановской транзакции больше лимита, вызов другого контракта из контракта или erc20 wrapper увеличивает размер транзакции
Выделение памяти в транзакции больше лимита, нужны специальные контракты
Запись в storage больше лимита, лимит ~9мб
stack overflow и stack underflow
"""

FAUCET_TEST_DATA = [(1), (5), (999), (1_0000), (20_000)]
FAUCET_REQUEST_MESSAGE = "requesting faucet for Neon"


@allure.story("Basic: single user tests")
class TestSingleClient(BaseMixin):
    @pytest.mark.only_stands
    def test_create_account_and_get_balance(self):
        """Create account and get balance"""
        account = self.create_account()
        self.assert_balance(account.address, 0)

    @pytest.mark.only_stands
    def test_check_tokens_in_wallet_neon(self):
        """Check tokens in wallet: neon"""
        account = self.create_account()
        with allure.step(FAUCET_REQUEST_MESSAGE):
            self.request_faucet_neon(account.address, InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(account.address, InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_check_tokens_in_wallet_spl(self):
        """Check tokens in wallet: spl"""
        pass

    @pytest.mark.skip(WAITING_FOR_ERC20)
    def test_check_tokens_in_wallet_ERC20(self):
        """Check tokens in wallet: ERC20"""
        pass

    @pytest.mark.only_stands
    @pytest.mark.parametrize("amount", FAUCET_TEST_DATA)
    def test_verify_faucet_work_single_request(self, amount: int):
        """Verify faucet work (request drop for several accounts): single request"""
        for _ in range(10):
            account = self.create_account()
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, amount)
            self.assert_balance(account.address, amount)

    @pytest.mark.only_stands
    @pytest.mark.parametrize("amount", FAUCET_TEST_DATA)
    def test_verify_faucet_work_multiple_requests(self, amount: int):
        """Verify faucet work (request drop for several accounts): double request"""
        for _ in range(10):
            account = self.create_account()
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, amount)
            with allure.step(FAUCET_REQUEST_MESSAGE):
                self.request_faucet_neon(account.address, InputData.FAUCET_2ND_REQUEST_AMOUNT.value)
            self.assert_balance(account.address, amount + InputData.FAUCET_2ND_REQUEST_AMOUNT.value)
