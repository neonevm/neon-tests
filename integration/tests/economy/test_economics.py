import json
import logging
import random
import time
from decimal import Decimal, getcontext

import allure
import pytest
import rlp
import solcx
from _pytest.config import Config
from solana.keypair import Keypair as SolanaAccount
from solana.publickey import PublicKey
from solana.rpc.core import RPCException
from solana.rpc.types import Commitment, TxOpts
from solana.transaction import Transaction
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
)

from utils.consts import LAMPORT_PER_SOL
from utils.erc20 import ERC20
from utils.helpers import wait_condition

from ..base import BaseTests
from ..basic.helpers.chains import make_nonce_the_biggest_for_chain

TX_COST = 5000

DECIMAL_CONTEXT = getcontext()
DECIMAL_CONTEXT.prec = 9

SOLCX_VERSIONS = ["0.6.6", "0.8.6", "0.8.10"]

INSUFFICIENT_FUNDS_ERROR = "insufficient funds for"
GAS_LIMIT_ERROR = "gas limit reached"
LOGGER = logging.getLogger(__name__)
BIG_STRING = (
    "But I must explain to you how all this mistaken idea of denouncing pleasure and "
    "praising pain was born and I will give you a complete account of the system, and "
    "expound the actual teachings of the great explorer of the truth, the master-builder "
    "of human happiness. No one rejects, dislikes, or avoids pleasure itself, because it"
    " is pleasure, but because those who do not know how to pursue pleasure rationally"
    " encounter consequences that are extremely painful. Nor again is there anyone who"
    " loves or pursues or desires to obtain pain of itself, because it is pain, but"
    " because occasionally circumstances occur in which toil and pain can procure him"
    " some great pleasure. To take a trivial example, which of us ever undertakes laborious"
    " physical exercise, except to obtain some advantage from it? But who has any right to"
    " find fault with a man who chooses to enjoy a pleasure that has no annoying consequences,"
    " or one who avoids a pain that produces no resultant pleasure? On the other hand,"
    " we denounce with righteous indigna"
    " some great pleasure. To take a trivial example, which of us ever undertakes laborious"
    " physical exercise, except to obtain some advantage from it? But who has any right to"
)


# @pytest.fixture(scope="session", autouse=True)
# def heat_stand(web3_client: web3client.NeonChainWeb3Client, faucet):
#     """After redeploy stand, first 10-20 requests spend more sols than expected."""
#     if "CI" not in os.environ:
#         return
#     acc = web3_client.eth.account.create()
#     faucet.request_neon(acc.address, 100)
#     for _ in range(50):
#         web3_client.send_neon(acc, web3_client.eth.account.create(), 1)


@pytest.fixture(scope="session", autouse=True)
def install_solcx_versions():
    for version in SOLCX_VERSIONS:
        solcx.install_solc(version)


@allure.story("Operator economy")
class TestEconomics(BaseTests):
    acc = None

    @pytest.fixture(autouse=True)
    def save_token_costs(self, sol_price, neon_price):
        self.sol_price = sol_price
        self.neon_price = neon_price

    @allure.step("Verify operator profit")
    def assert_profit(self, sol_diff, token_diff, token_price, token_name):
        sol_amount = sol_diff / LAMPORT_PER_SOL
        if token_diff < 0:
            raise AssertionError(f"NEON has negative difference {token_diff}")
        sol_cost = Decimal(sol_amount, DECIMAL_CONTEXT) * Decimal(self.sol_price, DECIMAL_CONTEXT)
        token_cost = Decimal(token_diff, DECIMAL_CONTEXT) * Decimal(token_price, DECIMAL_CONTEXT)

        msg = "Operator receive {:.9f} {} ({:.2f} $) and spend {:.9f} SOL ({:.2f} $), profit - {:.9f}% ".format(
            token_diff,
            token_name,
            token_cost,
            sol_amount,
            sol_cost,
            ((token_cost - sol_cost) / sol_cost * 100),
        )
        print(msg)
        with allure.step(msg):
            assert token_cost > sol_cost, msg

    @allure.step("Get single transaction gas")
    def get_single_transaction_gas(self):
        """One TX_COST to verify Solana signature plus another one TX_COST to pay to Governance"""
        return TX_COST * 2

    @allure.step("Check transaction used ALT")
    def check_alt_on(self, sol_client, receipt, accounts_quantity):
        solana_trx = self.web3_client.get_solana_trx_by_neon(receipt["transactionHash"].hex())
        wait_condition(
            lambda: sol_client.get_transaction(
                Signature.from_string(solana_trx["result"][0]),
                max_supported_transaction_version=0,
            )
            != GetTransactionResp(None)
        )
        trx = sol_client.get_transaction(
            Signature.from_string(solana_trx["result"][0]),
            max_supported_transaction_version=0,
        )
        alt = trx.value.transaction.transaction.message.address_table_lookups
        accounts = alt[0].writable_indexes + alt[0].readonly_indexes
        assert len(accounts) == accounts_quantity - 2

    @allure.step("Check block for not using ALT")
    def check_alt_off(self, block):
        txs = block.value.transactions
        for tx in txs:
            if tx.version == 0 and tx.transaction.message.address_table_lookups:
                raise AssertionError("ALT should not be used")

    @allure.step("Get gas used percent")
    def get_gas_used_percent(self, receipt):
        trx = self.web3_client.eth.get_transaction(receipt["transactionHash"])
        estimated_gas = trx["gas"]
        percent = round(receipt["gasUsed"] / estimated_gas * 100, 2)
        with allure.step(f"Gas used percent: {percent}%"):
            pass

    @pytest.mark.only_stands
    def test_account_creation(self, client_and_price):
        """Verify account creation spend SOL"""
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_token_balance(w3_client)
        acc = w3_client.eth.account.create()
        assert w3_client.get_balance(acc.address) == Decimal(0)
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_token_balance(w3_client)
        assert neon_balance_after == neon_balance_before
        assert sol_balance_after == sol_balance_before

    def test_send_neon_to_unexist_account(self, account_with_all_tokens, client_and_price):
        """Verify how many cost transfer of native chain token to new user"""
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)
        transfer_value = 50000000
        acc2 = w3_client.create_account()
        receipt = w3_client.send_tokens(account_with_all_tokens, acc2, transfer_value)
        assert w3_client.get_balance(acc2) == transfer_value

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after, "Operator SOL balance incorrect"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(sol_diff, token_diff, token_price, w3_client.native_token_name)
        self.get_gas_used_percent(receipt)

    def test_send_tokens_to_exist_account(self, account_with_all_tokens, client_and_price):
        """Verify how many cost token send to use who was already initialized"""
        w3_client, token_price = client_and_price
        acc2 = w3_client.create_account()
        transfer_value = 5000
        w3_client.send_tokens(account_with_all_tokens, acc2, transfer_value // 2)

        assert w3_client.get_balance(acc2) == transfer_value // 2

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)
        receipt = w3_client.send_tokens(account_with_all_tokens, acc2, transfer_value // 2)

        assert w3_client.get_balance(acc2) == transfer_value

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after
        self.get_gas_used_percent(receipt)

        assert sol_balance_before > sol_balance_after, "Operator balance after send tx doesn't changed"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(sol_diff, token_diff, token_price, w3_client.native_token_name)

    def test_send_when_not_enough_tokens_to_gas(self, client_and_price, account_with_all_tokens):
        w3_client, token_price = client_and_price
        acc2 = w3_client.create_account()

        assert w3_client.get_balance(acc2) == 0
        transfer_amount = 5000
        w3_client.send_tokens(account_with_all_tokens, acc2, transfer_amount)

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        acc3 = w3_client.create_account()

        with pytest.raises(ValueError, match=INSUFFICIENT_FUNDS_ERROR) as e:
            w3_client.send_tokens(acc2, acc3, transfer_amount)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after
        assert token_balance_before == token_balance_after

    def test_erc20wrapper_transfer(self, erc20_wrapper, client_and_price):
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)
        assert erc20_wrapper.contract.functions.balanceOf(self.acc.address).call() == 0
        transfer_tx = erc20_wrapper.transfer(erc20_wrapper.account, self.acc, 25)

        assert erc20_wrapper.contract.functions.balanceOf(self.acc.address).call() == 25
        wait_condition(lambda: sol_balance_before > self.operator.get_solana_balance())
        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)

        self.assert_profit(sol_diff, token_diff, token_price, w3_client.native_token_name)

        self.get_gas_used_percent(transfer_tx)

    def test_withdraw_neon_unexisting_ata(self, pytestconfig: Config):
        sol_user = SolanaAccount()
        self.sol_client.request_airdrop(sol_user.public_key, 5 * LAMPORT_PER_SOL)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_token_balance(self.web3_client)

        user_neon_balance_before = self.web3_client.get_balance(self.acc)
        move_amount = self.web3_client._web3.to_wei(5, "ether")

        contract, _ = self.web3_client.deploy_and_get_contract("precompiled/NeonToken", "0.8.10", account=self.acc)

        instruction_tx = contract.functions.withdraw(bytes(sol_user.public_key)).build_transaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
                "value": move_amount,
            }
        )
        receipt = self.web3_client.send_transaction(self.acc, instruction_tx)
        assert receipt["status"] == 1

        assert (user_neon_balance_before - self.web3_client.get_balance(self.acc)) > 5

        balance = self.sol_client.get_account_info_json_parsed(sol_user.public_key, commitment=Commitment("confirmed"))
        assert int(balance.value.lamports) == int(move_amount / 1_000_000_000)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_token_balance(self.web3_client)

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

        neon_diff = self.web3_client.to_main_currency(neon_balance_after - neon_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after,
            neon_diff,
            self.neon_price,
            self.web3_client.native_token_name,
        )

        self.get_gas_used_percent(receipt)

    def test_withdraw_neon_existing_ata(self, pytestconfig, neon_mint):
        sol_user = SolanaAccount()
        self.sol_client.request_airdrop(sol_user.public_key, 5 * LAMPORT_PER_SOL)

        wait_condition(lambda: self.sol_client.get_balance(sol_user.public_key) != 0)

        trx = Transaction()
        trx.add(create_associated_token_account(sol_user.public_key, sol_user.public_key, neon_mint))

        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.sol_client.send_transaction(trx, sol_user, opts=opts)

        dest_token_acc = get_associated_token_address(sol_user.public_key, neon_mint)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_token_balance(self.web3_client)

        user_neon_balance_before = self.web3_client.get_balance(self.acc)
        move_amount = self.web3_client._web3.to_wei(5, "ether")

        contract, _ = self.web3_client.deploy_and_get_contract("precompiled/NeonToken", "0.8.10", account=self.acc)

        instruction_tx = contract.functions.withdraw(bytes(sol_user.public_key)).build_transaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
                "value": move_amount,
            }
        )
        receipt = self.web3_client.send_transaction(self.acc, instruction_tx)
        assert receipt["status"] == 1

        assert (user_neon_balance_before - self.web3_client.get_balance(self.acc)) > 5

        balances = json.loads(
            self.sol_client.get_token_account_balance(dest_token_acc, Commitment("confirmed")).to_json()
        )
        assert int(balances["result"]["value"]["amount"]) == int(move_amount / 1_000_000_000)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_token_balance(self.web3_client)

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

        neon_diff = self.web3_client.to_main_currency(neon_balance_after - neon_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after,
            neon_diff,
            self.neon_price,
            self.web3_client.native_token_name,
        )
        self.get_gas_used_percent(receipt)

    def test_erc20_contract_deploy(self, client_and_price, account_with_all_tokens, web3_client_sol, web3_client):
        """Verify ERC20 contract deploy"""
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])

        contract, contract_deploy_tx = w3_client.deploy_and_get_contract(
            "EIPs/ERC20/ERC20.sol",
            "0.8.8",
            account_with_all_tokens,
            constructor_args=["Test Token", "TT", 1000],
        )
        assert contract.functions.balanceOf(account_with_all_tokens.address).call() == 1000

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(sol_diff, token_diff, token_price, w3_client.native_token_name)
        self.get_gas_used_percent(contract_deploy_tx)

    def test_erc20_transfer(self, client_and_price, account_with_all_tokens, web3_client_sol, web3_client):
        """Verify ERC20 token send"""
        w3_client, token_price = client_and_price
        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        contract = ERC20(w3_client, self.faucet, owner=account_with_all_tokens)

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        acc2 = w3_client.create_account()

        transfer_tx = contract.transfer(account_with_all_tokens, acc2, 25)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)
        sol_diff = sol_balance_before - sol_balance_after

        assert sol_balance_before > sol_balance_after
        assert token_balance_after > token_balance_before

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(sol_diff, token_diff, token_price, w3_client.native_token_name)
        self.get_gas_used_percent(transfer_tx)

    def test_deploy_small_contract_less_100tx(self, account_with_all_tokens, client_and_price, web3_client_sol,
                                              web3_client):
        """Verify we are bill minimum for 100 instruction"""
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        contract, _ = w3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=account_with_all_tokens)

        sol_balance_after_deploy = self.operator.get_solana_balance()
        token_balance_after_deploy = self.operator.get_token_balance(w3_client)
        tx = self.create_tx_object(account_with_all_tokens.address, estimate_gas=False, web3_client=w3_client)
        inc_tx = contract.functions.inc().build_transaction(tx)

        assert contract.functions.get().call() == 0
        receipt = w3_client.send_transaction(account_with_all_tokens, inc_tx)
        assert contract.functions.get().call() == 1

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after_deploy > sol_balance_after
        assert token_balance_after > token_balance_after_deploy > token_balance_before
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(sol_balance_before - sol_balance_after, token_diff, token_price, w3_client.native_token_name)
        self.get_gas_used_percent(receipt)

    def test_deploy_small_contract_less_gas(self, account_with_all_tokens, client_and_price):
        w3_client, token_price = client_and_price

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)
        with pytest.raises(ValueError, match=GAS_LIMIT_ERROR):
            w3_client.deploy_and_get_contract("common/Counter", "0.8.10", gas=1000, account=account_with_all_tokens)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after
        assert token_balance_after == token_balance_before

    def test_deploy_small_contract_less_tokens(self, account_with_all_tokens, client_and_price):
        w3_client, token_price = client_and_price
        acc2 = w3_client.create_account()
        w3_client.send_tokens(account_with_all_tokens, acc2, 10)

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        with pytest.raises(ValueError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=acc2)

        sol_balance_after_deploy = self.operator.get_solana_balance()
        token_balance_after_deploy = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after_deploy
        assert token_balance_before == token_balance_after_deploy

    def test_deploy_to_losted_contract_account(self, account_with_all_tokens, client_and_price):
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        acc2 = w3_client.create_account()
        w3_client.send_tokens(account_with_all_tokens, acc2, 1)

        with pytest.raises(ValueError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=acc2)
        w3_client.send_tokens(account_with_all_tokens, acc2, int(w3_client.get_balance(account_with_all_tokens) // 10))
        contract, contract_deploy_tx = w3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=acc2)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after
        assert token_balance_after > token_balance_before

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(sol_balance_before - sol_balance_after, token_diff, token_price, w3_client.native_token_name)
        self.get_gas_used_percent(contract_deploy_tx)

    def test_contract_get_is_free(self, counter_contract, client_and_price, account_with_all_tokens):
        """Verify that get contract calls is free"""
        w3_client, token_price = client_and_price
        sol_balance_after_deploy = self.operator.get_solana_balance()
        token_balance_after_deploy = self.operator.get_token_balance(w3_client)

        user_balance_before = w3_client.get_balance(account_with_all_tokens)
        assert counter_contract.functions.get().call() == 0

        assert w3_client.get_balance(account_with_all_tokens) == user_balance_before

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)
        assert sol_balance_after_deploy == sol_balance_after
        assert token_balance_after_deploy == token_balance_after

    @pytest.mark.xfail(reason="https://neonlabs.atlassian.net/browse/NDEV-699")
    def test_cost_resize_account(self):
        """Verify how much cost account resize"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_token_balance(self.web3_client)

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/IncreaseStorage", "0.8.10", account=self.acc
        )

        sol_balance_before_increase = self.operator.get_solana_balance()
        neon_balance_before_increase = self.operator.get_token_balance(self.web3_client)

        inc_tx = contract.functions.inc().build_transaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        instruction_receipt = self.web3_client.send_transaction(self.acc, inc_tx)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_token_balance(self.web3_client)

        assert sol_balance_before > sol_balance_before_increase > sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after > neon_balance_before_increase > neon_balance_before, "NEON Balance incorrect"
        neon_diff = self.web3_client.to_main_currency(neon_balance_after - neon_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after,
            neon_diff,
            self.neon_price,
            self.web3_client.native_token_name,
        )
        self.get_gas_used_percent(instruction_receipt)

    def test_cost_resize_account_less_tokens(self, account_with_all_tokens, client_and_price):
        """Verify how much cost account resize"""
        w3_client, token_price = client_and_price
        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [self.web3_client, self.web3_client_sol])
        contract, contract_deploy_tx = w3_client.deploy_and_get_contract(
            "common/IncreaseStorage", "0.8.10", account=account_with_all_tokens
        )

        acc2 = w3_client.create_account()
        w3_client.send_tokens(account_with_all_tokens, acc2, 1000)

        sol_balance_before_increase = self.operator.get_solana_balance()
        token_balance_before_increase = self.operator.get_token_balance(w3_client)

        tx = self.create_tx_object(acc2.address, estimate_gas=False, web3_client=w3_client)
        inc_tx = contract.functions.inc().build_transaction(tx)

        with pytest.raises(ValueError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.send_transaction(acc2, inc_tx)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before_increase == sol_balance_after, "SOL Balance not changed"
        assert token_balance_after == token_balance_before_increase, "TOKEN Balance incorrect"

    def test_failed_tx_when_less_gas(self, account_with_all_tokens, client_and_price):
        """Don't get money from user if tx failed"""
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        acc2 = w3_client.create_account()

        user_balance_before = w3_client.get_balance(account_with_all_tokens)
        with pytest.raises(ValueError, match=GAS_LIMIT_ERROR):
            w3_client.send_tokens(account_with_all_tokens, acc2, 5000, gas=100)

        assert user_balance_before == w3_client.get_balance(account_with_all_tokens)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after
        assert token_balance_after == token_balance_before

    def test_contract_interact_more_500_steps(self, counter_contract, client_and_price, account_with_all_tokens):
        """Deploy a contract with more 500 instructions"""
        w3_client, token_price = client_and_price

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)
        tx = self.create_tx_object(account_with_all_tokens.address, estimate_gas=False, web3_client=w3_client)
        instruction_tx = counter_contract.functions.moreInstruction(0, 100).build_transaction(tx)  # 1086 steps in evm
        instruction_receipt = w3_client.send_transaction(account_with_all_tokens, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(sol_balance_before - sol_balance_after, token_diff, token_price, w3_client.native_token_name)
        self.get_gas_used_percent(instruction_receipt)

    def test_contract_interact_more_steps(self, counter_contract, client_and_price, account_with_all_tokens):
        """Deploy a contract with more 500000 bpf"""
        w3_client, token_price = client_and_price

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)
        tx = self.create_tx_object(account_with_all_tokens.address, estimate_gas=False, web3_client=w3_client)
        instruction_tx = counter_contract.functions.moreInstruction(0, 1500).build_transaction(tx)

        instruction_receipt = w3_client.send_transaction(account_with_all_tokens, instruction_tx)
        wait_condition(lambda: sol_balance_before > self.operator.get_solana_balance())

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after,
            token_diff, token_price, w3_client.native_token_name
        )
        self.get_gas_used_percent(instruction_receipt)

    def test_contract_interact_more_steps_less_gas(self, counter_contract, client_and_price, account_with_all_tokens):
        """Interact a contract with more 500000 bpf and small amount of gas"""
        w3_client, token_price = client_and_price

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        tx = self.create_tx_object(account_with_all_tokens.address, estimate_gas=False, web3_client=w3_client, gas=1000)
        instruction_tx = counter_contract.functions.moreInstruction(0, 1500).build_transaction(tx)

        with pytest.raises(ValueError, match=GAS_LIMIT_ERROR):
            w3_client.send_transaction(account_with_all_tokens, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_after == sol_balance_before, "SOL Balance changes"
        assert token_balance_after == token_balance_before, "TOKEN Balance incorrect"

    def test_contract_interact_more_steps_less_tokens(self, counter_contract, client_and_price, account_with_all_tokens):
        """Deploy a contract with more 500000 bpf"""
        w3_client, token_price = client_and_price
        acc2 = w3_client.create_account()
        w3_client.send_tokens(account_with_all_tokens, acc2, 100)

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        tx = self.create_tx_object(acc2.address, estimate_gas=False, web3_client=w3_client)
        instruction_tx = counter_contract.functions.moreInstruction(0, 1500).build_transaction(tx)
        with pytest.raises(ValueError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.send_transaction(acc2, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after, "SOL Balance changed"
        assert token_balance_after == token_balance_before, "TOKEN Balance incorrect"

    # @pytest.mark.xfail(reason="Unprofitable transaction, because we create account not in evm (will be fixed)")
    def test_tx_interact_more_1kb(self, counter_contract, client_and_price, account_with_all_tokens):
        """Send to contract a big text (tx more than 1 kb)"""
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        tx = self.create_tx_object(account_with_all_tokens.address, estimate_gas=False, web3_client=w3_client)
        instruction_tx = counter_contract.functions.bigString(BIG_STRING).build_transaction(tx)

        instruction_receipt = w3_client.send_transaction(account_with_all_tokens, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after,
            token_diff, token_price, w3_client.native_token_name
        )
        self.get_gas_used_percent(instruction_receipt)

    def test_tx_interact_more_1kb_less_tokens(self, counter_contract, client_and_price, account_with_all_tokens):
        """Send to contract a big text (tx more than 1 kb) when less tokens"""
        w3_client, token_price = client_and_price

        acc2 = self.web3_client.create_account()
        w3_client.send_tokens(account_with_all_tokens, acc2, 1000)

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        tx = self.create_tx_object(acc2.address, estimate_gas=False, web3_client=w3_client)
        instruction_tx = counter_contract.functions.bigString(BIG_STRING).build_transaction(tx)
        with pytest.raises(ValueError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.send_transaction(acc2, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after, "SOL Balance changed"
        assert token_balance_after == token_balance_before, "TOKEN Balance incorrect"

    def test_tx_interact_more_1kb_less_gas(self, counter_contract, client_and_price, account_with_all_tokens):
        """Send to contract a big text (tx more than 1 kb)"""
        w3_client, token_price = client_and_price

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        tx = self.create_tx_object(account_with_all_tokens.address, estimate_gas=False, web3_client=w3_client, gas=100)
        instruction_tx = counter_contract.functions.bigString(BIG_STRING).build_transaction(tx)
        with pytest.raises(ValueError, match=GAS_LIMIT_ERROR):
            w3_client.send_transaction(account_with_all_tokens, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after, "SOL Balance changed"
        assert token_balance_after == token_balance_before, "TOKEN Balance incorrect"

    def test_deploy_contract_more_1kb(self, client_and_price, account_with_all_tokens, web3_client, web3_client_sol):
        w3_client, token_price = client_and_price

        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        contract, contract_deploy_tx = w3_client.deploy_and_get_contract(
            "common/Fat", "0.8.10", account=account_with_all_tokens
        )

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after
        assert token_balance_after > token_balance_before

        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after,
            token_diff, token_price, w3_client.native_token_name
        )
        self.get_gas_used_percent(contract_deploy_tx)

    def test_deploy_contract_more_1kb_less_tokens(self, client_and_price, account_with_all_tokens):
        w3_client, token_price = client_and_price
        acc2 = w3_client.create_account()
        w3_client.send_tokens(account_with_all_tokens, acc2, 100)

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        with pytest.raises(ValueError, match=INSUFFICIENT_FUNDS_ERROR):
            w3_client.deploy_and_get_contract("common/Fat", "0.8.10", account=acc2)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after
        assert token_balance_after == token_balance_before

    def test_deploy_contract_more_1kb_less_gas(self, client_and_price, account_with_all_tokens):
        w3_client, token_price = client_and_price
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        with pytest.raises(ValueError, match=GAS_LIMIT_ERROR):
            w3_client.deploy_and_get_contract("common/Fat", "0.8.10", account=account_with_all_tokens, gas=1000)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before == sol_balance_after
        assert token_balance_after == token_balance_before

    def test_deploy_contract_to_payed(self, client_and_price, account_with_all_tokens, web3_client, web3_client_sol):
        w3_client, token_price = client_and_price
        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        nonce = w3_client.eth.get_transaction_count(account_with_all_tokens.address)
        contract_address = w3_client.keccak(rlp.encode((bytes.fromhex(self.acc.address[2:]), nonce)))[-20:]

        w3_client.send_tokens(account_with_all_tokens, w3_client.to_checksum_address(contract_address.hex()), 5000)

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        contract, contract_deploy_tx = w3_client.deploy_and_get_contract(
            "common/Counter", "0.8.10", account=account_with_all_tokens
        )

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert token_balance_after > token_balance_before, "TOKEN Balance incorrect"
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after,
            token_diff,
            token_price, w3_client.native_token_name
        )
        self.get_gas_used_percent(contract_deploy_tx)

    def test_deploy_contract_to_exist_unpayed(self, client_and_price, account_with_all_tokens, web3_client, web3_client_sol):
        w3_client, token_price = client_and_price

        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        nonce = w3_client.eth.get_transaction_count(account_with_all_tokens.address)
        contract_address = w3_client.to_checksum_address(
            w3_client.keccak(rlp.encode((bytes.fromhex(account_with_all_tokens.address[2:]), nonce)))[-20:].hex()
        )
        with pytest.raises(ValueError, match=GAS_LIMIT_ERROR):
            w3_client.send_tokens(account_with_all_tokens, contract_address, 100, gas=1)

        _, contract_deploy_tx = w3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=account_with_all_tokens)

        sol_balance_after_deploy = self.operator.get_solana_balance()
        token_balance_after_deploy = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after_deploy
        assert token_balance_after_deploy > token_balance_before
        token_diff = w3_client.to_main_currency(token_balance_after_deploy - token_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after_deploy,
            token_diff,
            token_price, w3_client.native_token_name
        )
        self.get_gas_used_percent(contract_deploy_tx)

    @pytest.mark.timeout(960)
    def test_deploy_contract_alt_on(self, sol_client):
        """Trigger transaction than requires more than 30 accounts"""
        accounts_quantity = random.randint(31, 45)
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_token_balance(self.web3_client)

        contract, _ = self.web3_client.deploy_and_get_contract(
            "common/ALT", "0.8.10", account=self.acc, constructor_args=[8]
        )

        tx = contract.functions.fill(accounts_quantity).build_transaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        receipt = self.web3_client.send_transaction(self.acc, tx)
        self.check_alt_on(sol_client, receipt, accounts_quantity)
        solana_trx = self.web3_client.get_solana_trx_by_neon(receipt["transactionHash"].hex())
        sol_trx_with_alt = None

        for trx in solana_trx["result"]:
            trx_sol = sol_client.get_transaction(
                Signature.from_string(trx),
                max_supported_transaction_version=0,
            )
            if trx_sol.value.transaction.transaction.message.address_table_lookups:
                sol_trx_with_alt = trx_sol

        if not sol_trx_with_alt:
            raise ValueError(f"There are no lookup table for {solana_trx}")

        operator = PublicKey(sol_trx_with_alt.value.transaction.transaction.message.account_keys[0])

        alt_address = sol_trx_with_alt.value.transaction.transaction.message.address_table_lookups[0].account_key
        alt_balance = sol_client.get_balance(PublicKey(alt_address)).value
        operator_balance = sol_client.get_balance(operator).value

        wait_condition(
            lambda: self.operator.get_solana_balance() != sol_balance_before,
            timeout_sec=120,
        )
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_token_balance(self.web3_client)

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before
        neon_diff = self.web3_client.to_main_currency(neon_balance_after - neon_balance_before)
        self.assert_profit(
            sol_balance_before - sol_balance_after - alt_balance,
            neon_diff,
            self.neon_price, self.web3_client.native_token_name
        )
        # the charge for alt creating should be returned
        wait_condition(
            lambda: sol_client.get_balance(operator).value > operator_balance,
            timeout_sec=60 * 15,
            delay=3,
        )

        assert (
            operator_balance + alt_balance - TX_COST * 2 == sol_client.get_balance(operator).value
        ), "Operator balance after the return of the alt creation fee is not correct"
        self.get_gas_used_percent(receipt)

    def test_deploy_contract_alt_off(self, sol_client, client_and_price, account_with_all_tokens, web3_client, web3_client_sol):
        """Trigger transaction than requires less than 30 accounts"""
        accounts_quantity = 10
        w3_client, token_price = client_and_price
        make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
        sol_balance_before = self.operator.get_solana_balance()
        token_balance_before = self.operator.get_token_balance(w3_client)

        contract, _ = w3_client.deploy_and_get_contract(
            "common/ALT", "0.8.10", account=account_with_all_tokens, constructor_args=[8]
        )

        sol_balance_after_deploy = self.operator.get_solana_balance()
        token_balance_after_deploy = self.operator.get_token_balance(w3_client)

        tx = self.create_tx_object(account_with_all_tokens.address, estimate_gas=False, web3_client=w3_client)
        intr = contract.functions.fill(accounts_quantity).build_transaction(tx)
        receipt = w3_client.send_transaction(account_with_all_tokens, intr)
        block = int(receipt["blockNumber"])

        response = wait_for_block(sol_client, block)
        self.check_alt_off(response)

        sol_balance_after = self.operator.get_solana_balance()
        token_balance_after = self.operator.get_token_balance(w3_client)

        assert sol_balance_before > sol_balance_after_deploy > sol_balance_after
        assert token_balance_after > token_balance_after_deploy > token_balance_before
        token_diff = w3_client.to_main_currency(token_balance_after - token_balance_after_deploy)
        self.assert_profit(
            sol_balance_after_deploy - sol_balance_after,
            token_diff, token_price, w3_client.native_token_name
        )
        self.get_gas_used_percent(receipt)


def wait_for_block(client, block, timeout=60):
    started = time.time()
    while (time.time() - started) < timeout:
        try:
            return client.get_block(block, max_supported_transaction_version=2)
        except RPCException:
            time.sleep(3)
        time.sleep(3)
    raise TimeoutError("Block not available for slot")
