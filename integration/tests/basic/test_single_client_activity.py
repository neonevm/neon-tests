import allure
import pytest

from integration.tests.basic.helper_methods import FIRST_FAUCET_REQUEST_AMOUNT, SECOND_FAUCET_REQUEST_AMOUNT, \
    BasicHelpers


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


'''
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
'''


@allure.story("Basic: single user tests")
class TestSingleClient(BasicHelpers):
    @allure.step("test: create account and get balance")
    def test_create_account_and_get_balance(self):
        '''Create account and get balance'''
        account = self.create_account()
        self.assert_amount(account.address, 0)

    @allure.step("test: check tokens in wallet: neon")
    def test_check_tokens_in_wallet_neon(self):
        '''Check tokens in wallet: neon'''
        account = self.create_account()
        self.request_faucet_neon(account.address, FIRST_FAUCET_REQUEST_AMOUNT)
        self.assert_amount(account.address, FIRST_FAUCET_REQUEST_AMOUNT)

    @pytest.mark.skip("not yet done")
    @allure.step("test: check tokens in wallet: spl")
    def test_check_tokens_in_wallet_spl(self):
        '''Check tokens in wallet: spl'''
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: check tokens in wallet: ERC20")
    def test_check_tokens_in_wallet_ERC20(self):
        '''Check tokens in wallet: ERC20'''
        pass

    @allure.step(
        "test: verify faucet work (request drop for several accounts): single request"
    )
    def test_verify_faucet_work_single_request(self):
        '''Verify faucet work (request drop for several accounts): single request'''
        for _ in range(10):
            account = self.create_account()
            self.request_faucet_neon(account.address,
                                     FIRST_FAUCET_REQUEST_AMOUNT)
            self.assert_amount(account.address, FIRST_FAUCET_REQUEST_AMOUNT)

    @allure.step(
        "test: verify faucet work (request drop for several accounts): double request"
    )
    def test_verify_faucet_work_multiple_requests(self):
        '''Verify faucet work (request drop for several accounts): double request'''
        for _ in range(10):
            account = self.create_account()
            self.request_faucet_neon(account.address,
                                     FIRST_FAUCET_REQUEST_AMOUNT)
            self.request_faucet_neon(account.address,
                                     SECOND_FAUCET_REQUEST_AMOUNT)
            self.assert_amount(
                account.address,
                FIRST_FAUCET_REQUEST_AMOUNT + SECOND_FAUCET_REQUEST_AMOUNT)
