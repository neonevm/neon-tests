import typing as tp
from decimal import Decimal, getcontext

import allure
import eth_account.signers.local
import pytest
import rlp
import solcx
import time
from _pytest.config import Config
from solana.keypair import Keypair as SolanaAccount
from solana.publickey import PublicKey
from solana.rpc.types import TokenAccountOpts, Commitment
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.instructions import create_associated_token_account, get_associated_token_address

from ..base import BaseTests
from utils import helpers

NEON_PRICE = 0.25

LAMPORT_PER_SOL = 1_000_000_000
DECIMAL_CONTEXT = getcontext()
DECIMAL_CONTEXT.prec = 9

SOLCX_VERSIONS = ["0.6.6", "0.8.6", "0.8.10"]


@pytest.fixture(scope="session", autouse=True)
def install_solcx_versions():
    for version in SOLCX_VERSIONS:
        solcx.install_solc(version)


@allure.story("Operator economy")
class TestEconomics(BaseTests):
    acc = None

    @pytest.fixture(autouse=True)
    def setup_sol_cost(self, sol_price):
        self.sol_price = sol_price

    @allure.step("Verify operator profit")
    def assert_profit(self, sol_diff, neon_diff):
        sol_amount = sol_diff / LAMPORT_PER_SOL
        if neon_diff < 0:
            raise AssertionError(f"NEON has negative difference {neon_diff}")
        # neon_amount = self.web3_client.fromWei(neon_diff, "ether")
        neon_amount = neon_diff
        sol_cost = Decimal(sol_amount, DECIMAL_CONTEXT) * Decimal(self.sol_price, DECIMAL_CONTEXT)
        neon_cost = Decimal(neon_amount, DECIMAL_CONTEXT) * Decimal(NEON_PRICE, DECIMAL_CONTEXT)
        msg = "Operator receive {:.9f} NEON ({:.2f} $) and spend {:.9f} SOL ({:.2f} $), profit - {:.9f}% ".format(
            neon_amount, neon_cost, sol_amount, sol_cost, ((neon_cost - sol_cost) / sol_cost * 100)
        )
        with allure.step(msg):
            assert neon_cost > sol_cost, msg

    @pytest.mark.only_stands
    def test_account_creation(self):
        """Verify account creation spend SOL"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()
        acc = self.web3_client.eth.account.create()
        assert self.web3_client.eth.get_balance(acc.address) == Decimal(0)
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert neon_balance_after == neon_balance_before
        assert sol_balance_after == sol_balance_before

    @pytest.mark.only_stands
    def test_send_neon_to_unexist_account(self):
        """Verify how many cost neon send to new user"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        acc2 = self.web3_client.create_account()

        tx = self.web3_client.send_neon(self.acc, acc2, 5)

        assert self.web3_client.get_balance(acc2) == 5

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after, "Operator balance after getBalance doesn't changed"
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    @pytest.mark.only_stands
    def test_send_neon_to_exist_account(self):
        """Verify how many cost neon send to use who was already initialized"""
        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 1)

        assert self.web3_client.get_balance(acc2) == 1

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()
        tx = self.web3_client.send_neon(self.acc, acc2, 5)

        assert self.web3_client.get_balance(acc2) == 6

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert sol_balance_before > sol_balance_after, "Operator balance after send tx doesn't changed"

        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_send_when_not_enough_for_gas(self):
        acc2 = self.web3_client.create_account()

        assert self.web3_client.get_balance(acc2) == 0

        self.web3_client.send_neon(self.acc, acc2, 1)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        acc3 = self.web3_client.create_account()

        with pytest.raises(ValueError, match=r"The account balance is less than required.*") as e:
            self.web3_client.send_neon(acc2, acc3, 1)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before == sol_balance_after
        assert neon_balance_before == neon_balance_after

    def test_erc20wrapper_transfer(self, erc20wrapper):
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, spl_owner = erc20wrapper

        assert contract.functions.balanceOf(self.acc.address).call() == 0

        transfer_tx = self.web3_client.send_erc20(spl_owner, self.acc, 25, contract.address, abi=contract.abi)

        assert contract.functions.balanceOf(self.acc.address).call() == 25
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after

        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_withdraw_neon_unexisting_ata(self, pytestconfig: Config):
        sol_user = SolanaAccount()
        self.sol_client.request_airdrop(sol_user.public_key, 5 * LAMPORT_PER_SOL)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract_interface = helpers.get_contract_interface("NeonToken.sol", "0.8.10")
        contract = self.web3_client.eth.contract(
            address=pytestconfig.environment.neon_erc20wrapper_address, abi=contract_interface["abi"]
        )

        user_neon_balance_before = self.web3_client.get_balance(self.acc)
        move_amount = self.web3_client._web3.toWei(5, "ether")

        instruction_tx = contract.functions.withdraw(bytes(sol_user.public_key)).buildTransaction(
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
        sol_balances = self.sol_client.get_token_accounts_by_owner(
            sol_user.public_key,
            TokenAccountOpts(mint=pytestconfig.environment.spl_neon_mint, encoding="jsonParsed"),
            Commitment("confirmed"),
        )["result"]

        assert int(sol_balances["value"][0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"]) == int(
            move_amount / 1_000_000_000
        )

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_withdraw_neon_existing_ata(self, pytestconfig):
        neon_mint = PublicKey(pytestconfig.environment.spl_neon_mint)
        sol_user = SolanaAccount()
        self.sol_client.request_airdrop(sol_user.public_key, 5 * LAMPORT_PER_SOL)

        for _ in range(6):
            if self.sol_client.get_balance(sol_user.public_key) != 0:
                break
            time.sleep(10)

        trx = Transaction()
        trx.add(create_associated_token_account(sol_user.public_key, sol_user.public_key, neon_mint))

        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.sol_client.send_transaction(trx, sol_user, opts=opts)

        dest_token_acc = get_associated_token_address(sol_user.public_key, neon_mint)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract_interface = helpers.get_contract_interface("NeonToken.sol", "0.8.10")
        contract = self.web3_client.eth.contract(
            address=pytestconfig.environment.neon_erc20wrapper_address, abi=contract_interface["abi"]
        )

        user_neon_balance_before = self.web3_client.get_balance(self.acc)
        move_amount = self.web3_client._web3.toWei(5, "ether")

        instruction_tx = contract.functions.withdraw(bytes(sol_user.public_key)).buildTransaction(
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
        assert (
            int(
                self.sol_client.get_token_account_balance(dest_token_acc, Commitment("confirmed"))["result"]["value"][
                    "amount"
                ]
            )
            == move_amount / 1_000_000_000
        )

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_erc20_contract(self):
        """Verify ERC20 token send"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20", "0.6.6", account=self.acc, constructor_args=[1000]
        )

        assert contract.functions.balanceOf(self.acc.address).call() == 1000

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after

        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_erc20_transfer(self):
        """Verify ERC20 token send"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20", "0.6.6", account=self.acc, constructor_args=[1000]
        )

        assert contract.functions.balanceOf(self.acc.address).call() == 1000

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        acc2 = self.web3_client.create_account()

        transfer_tx = self.web3_client.send_erc20(
            self.acc, acc2, 500, contract_deploy_tx["contractAddress"], abi=contract.abi
        )
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_deploy_small_contract_less_100tx(self, sol_price):
        """Verify we are bill minimum for 100 instruction"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        sol_balance_after_deploy = self.operator.get_solana_balance()
        neon_balance_after_deploy = self.operator.get_neon_balance()

        inc_tx = contract.functions.inc().buildTransaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        instruction_receipt = self.web3_client.send_transaction(self.acc, inc_tx)

        assert contract.functions.get().call() == 1

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after_deploy > sol_balance_after
        assert neon_balance_after > neon_balance_after_deploy > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    @pytest.mark.xfail(AssertionError, reason="This tx unprofitable because we create accounts before check gas")
    def test_deploy_small_contract_less_gas(self):
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", gas=1000)

        assert contract_deploy_tx["status"] == 0

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_deploy_small_contract_less_neon(self):
        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 0.001)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        with pytest.raises(ValueError, match="The account balance is less than required"):
            contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=acc2)

        sol_balance_after_deploy = self.operator.get_solana_balance()
        neon_balance_after_deploy = self.operator.get_neon_balance()

        assert sol_balance_before == sol_balance_after_deploy
        assert neon_balance_before == neon_balance_after_deploy

    def test_deploy_to_losted_contract_account(self):
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 0.001)

        with pytest.raises(ValueError, match="The account balance is less than required"):
            self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=acc2)

        self.web3_client.send_neon(self.acc, acc2, 50)
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=acc2)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_contract_get_is_free(self):
        """Verify that get contract calls is free"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        sol_balance_after_deploy = self.operator.get_solana_balance()
        neon_balance_after_deploy = self.operator.get_neon_balance()

        user_balance_before = self.web3_client.get_balance(self.acc)
        assert contract.functions.get().call() == 0

        assert self.web3_client.get_balance(self.acc) == user_balance_before

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert sol_balance_after_deploy == sol_balance_after
        assert neon_balance_after_deploy == neon_balance_after

    def test_cost_resize_account(self):
        """Verify how much cost account resize"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "IncreaseStorage", "0.8.10", account=self.acc
        )

        sol_balance_before_increase = self.operator.get_solana_balance()
        neon_balance_before_increase = self.operator.get_neon_balance()

        inc_tx = contract.functions.inc().buildTransaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        instruction_receipt = self.web3_client.send_transaction(self.acc, inc_tx)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_before_increase > sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after > neon_balance_before_increase > neon_balance_before, "NEON Balance incorrect"
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_cost_resize_account_less_neon(self):
        """Verify how much cost account resize"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "IncreaseStorage", "0.8.10", account=self.acc
        )

        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 0.001)

        sol_balance_before_increase = self.operator.get_solana_balance()
        neon_balance_before_increase = self.operator.get_neon_balance()

        inc_tx = contract.functions.inc().buildTransaction(
            {
                "from": acc2.address,
                "nonce": self.web3_client.eth.get_transaction_count(acc2.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        with pytest.raises(ValueError, match="The account balance is less than required"):
            self.web3_client.send_transaction(acc2, inc_tx)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before_increase == sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after == neon_balance_before_increase, "NEON Balance incorrect"

    @pytest.mark.xfail(AssertionError, reason="This tx unprofitable because we create accounts before check gas")
    def test_failed_tx_when_less_gas(self):
        """Don't get money from user if tx failed"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        acc2 = self.web3_client.create_account()

        balance_user_balance_before = self.web3_client.get_balance(self.acc)

        receipt = self.web3_client.send_neon(self.acc, acc2, 5, gas=100)

        assert receipt["status"] == 0

        assert balance_user_balance_before > self.web3_client.get_balance(self.acc)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_contract_interact_more_500_steps(self):
        """Deploy a contract with more 500 instructions"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        sol_balance_before_instruction = self.operator.get_solana_balance()
        neon_balance_before_instruction = self.operator.get_neon_balance()

        instruction_tx = contract.functions.moreInstruction(0, 15).buildTransaction(  # 1086 steps in evm
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        instruction_receipt = self.web3_client.send_transaction(self.acc, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_before_instruction > sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after > neon_balance_before_instruction > neon_balance_before, "NEON Balance incorrect"
        self.assert_profit(
            sol_balance_before_instruction - sol_balance_after, neon_balance_after - neon_balance_before_instruction
        )

    @pytest.mark.xfail(reason="Strange when more 200000 instructions")
    def test_contract_interact_more_500000_bpf(self):
        """Deploy a contract with more 500000 bpf"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        sol_balance_before_instruction = self.operator.get_solana_balance()
        neon_balance_before_instruction = self.operator.get_neon_balance()

        instruction_tx = contract.functions.moreInstruction(0, 5000).buildTransaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        instruction_receipt = self.web3_client.send_transaction(self.acc, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before_instruction > sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after > neon_balance_before_instruction, "NEON Balance incorrect"

        self.assert_profit(
            sol_balance_before_instruction - sol_balance_after, neon_balance_after - neon_balance_before_instruction
        )

    @pytest.mark.xfail(reason="Strange when more 200000 instructions")
    def test_contract_interact_more_500000_bpf_less_gas(self):
        """Deploy a contract with more 500000 bpf"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10")

        sol_balance_before_instruction = self.operator.get_solana_balance()
        neon_balance_before_instruction = self.operator.get_neon_balance()

        instruction_tx = contract.functions.moreInstruction(0, 50000).buildTransaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        receipt = self.web3_client.send_transaction(self.acc, instruction_tx, gas=1000)

        assert receipt["status"] == 0

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_after > sol_balance_before_instruction, "SOL Balance didn't change"
        assert neon_balance_after > neon_balance_before_instruction, "NEON Balance incorrect"

    def test_contract_interact_more_500000_bpf_less_neon(self):
        """Deploy a contract with more 500000 bpf"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 0.001)

        sol_balance_before_instruction = self.operator.get_solana_balance()
        neon_balance_before_instruction = self.operator.get_neon_balance()

        instruction_tx = contract.functions.moreInstruction(0, 5000).buildTransaction(
            {
                "from": acc2.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        with pytest.raises(ValueError, match="The account balance is less than required"):
            self.web3_client.send_transaction(acc2, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before_instruction == sol_balance_after, "SOL Balance changed"
        assert neon_balance_after == neon_balance_before_instruction, "NEON Balance incorrect"

    def test_tx_interact_more_1kb(self):
        """Send to contract a big text (tx more than 1 kb)"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        sol_balance_before_instruction = self.operator.get_solana_balance()
        neon_balance_before_instruction = self.operator.get_neon_balance()

        instruction_tx = contract.functions.bigString(
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
        ).buildTransaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        instruction_receipt = self.web3_client.send_transaction(self.acc, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_before_instruction > sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after > neon_balance_before_instruction > neon_balance_before, "NEON Balance incorrect"

        self.assert_profit(
            sol_balance_before_instruction - sol_balance_after, neon_balance_after - neon_balance_before_instruction
        )

    def test_tx_interact_more_1kb_less_neon(self):
        """Send to contract a big text (tx more than 1 kb) when less neon"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 0.001)

        sol_balance_before_instruction = self.operator.get_solana_balance()
        neon_balance_before_instruction = self.operator.get_neon_balance()

        instruction_tx = contract.functions.bigString(
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
        ).buildTransaction(
            {
                "from": acc2.address,
                "nonce": self.web3_client.eth.get_transaction_count(acc2.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        with pytest.raises(ValueError, match="The account balance is less than required"):
            instruction_receipt = self.web3_client.send_transaction(acc2, instruction_tx)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before_instruction == sol_balance_after, "SOL Balance changed"
        assert neon_balance_after == neon_balance_before_instruction, "NEON Balance incorrect"

    @pytest.mark.xfail(AssertionError, reason="This tx unprofitable because we create accounts before check gas")
    def test_tx_interact_more_1kb_less_gas(self):
        """Send to contract a big text (tx more than 1 kb)"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        instruction_tx = contract.functions.bigString(
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
        ).buildTransaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
                "gas": 100,
            }
        )
        receipt = self.web3_client.send_transaction(self.acc, instruction_tx, gas=100)

        assert receipt["status"] == 0

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after, "SOL Balance changed"
        assert neon_balance_after > neon_balance_before, "NEON Balance incorrect"
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_deploy_contract_more_1kb(self):
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Fat", "0.8.10", account=self.acc)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_deploy_contract_more_1kb_less_neon(self):
        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 0.001)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        with pytest.raises(ValueError, match="The account balance is less than required"):
            contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Fat", "0.8.10", account=acc2)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before == sol_balance_after
        assert neon_balance_after == neon_balance_before

    def test_deploy_contract_more_1kb_less_gas(self):
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "Fat", "0.8.10", account=self.acc, gas=1000
        )

        assert contract_deploy_tx["status"] == 0

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before

    def test_deploy_contract_to_payed(self):
        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 10)

        nonce = self.web3_client.eth.get_transaction_count(self.acc.address)
        contract_address = self.web3_client.keccak(rlp.encode((bytes.fromhex(self.acc.address[2:]), nonce)))[-20:]

        self.web3_client.send_neon(acc2, self.web3_client.toChecksumAddress(contract_address.hex()), 0.5)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after > neon_balance_before, "NEON Balance incorrect"
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_deploy_contract_to_exist_unpayed(self):
        acc2 = self.web3_client.create_account()
        self.web3_client.send_neon(self.acc, acc2, 50)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        nonce = self.web3_client.eth.get_transaction_count(acc2.address)
        contract_address = self.web3_client.toChecksumAddress(
            self.web3_client.keccak(rlp.encode((bytes.fromhex(acc2.address[2:]), nonce)))[-20:].hex()
        )

        self.web3_client.send_neon(acc2, contract_address, 1, gas=1)

        self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=acc2)

        sol_balance_after_deploy = self.operator.get_solana_balance()
        neon_balance_after_deploy = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after_deploy
        assert neon_balance_after_deploy > neon_balance_before
        self.assert_profit(
            sol_balance_before - sol_balance_after_deploy, neon_balance_after_deploy - neon_balance_before
        )

    def test_interact_with_contract_from_non_payed_user(self):
        acc2 = self.web3_client.create_account()
        self.faucet.request_neon(acc2.address, 10)

        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract("Counter", "0.8.10", account=self.acc)

        sol_balance_after_deploy = self.operator.get_solana_balance()
        neon_balance_after_deploy = self.operator.get_neon_balance()

        inc_tx = contract.functions.inc().buildTransaction(
            {
                "from": acc2.address,
                "nonce": self.web3_client.eth.get_transaction_count(acc2.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        instruction_receipt = self.web3_client.send_transaction(acc2, inc_tx)

        assert contract.functions.get().call() == 1

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after_deploy > sol_balance_after
        assert neon_balance_after > neon_balance_after_deploy > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)
