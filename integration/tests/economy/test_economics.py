import pathlib
import time
from decimal import Decimal, getcontext

import pytest
import solcx
import allure

from ..base import BaseTests


SOL_PRICE = 100
NEON_PRICE = 0.25

LAMPORT_PER_SOL = 1000000000
DECIMAL_CONTEXT = getcontext()
DECIMAL_CONTEXT.prec = 9


@pytest.fixture(scope="class")
def prepare_account(operator, faucet, web3_client):
    """Create new account for tests and save operator pre/post balances"""
    start_neon_balance = operator.get_neon_balance()
    start_sol_balance = operator.get_solana_balance()
    with allure.step(f"Operator initial balance: {start_neon_balance / LAMPORT_PER_SOL} NEON {start_sol_balance / LAMPORT_PER_SOL} SOL"):
        pass
    with allure.step("Create account for tests"):
        acc = web3_client.eth.account.create()
    with allure.step(f"Request 100 NEON from faucet for {acc.address}"):
        faucet.request_neon(acc.address, 100)
        assert web3_client.get_balance(acc) == 100
    yield acc
    end_neon_balance = operator.get_neon_balance()
    end_sol_balance = operator.get_solana_balance()
    with allure.step(f"Operator end balance: {end_neon_balance / LAMPORT_PER_SOL} NEON {end_sol_balance / LAMPORT_PER_SOL} SOL"):
        pass


@allure.story("Operator economy")
class TestEconomics(BaseTests):
    acc = None

    @allure.step("Verify operator profit")
    def assert_profit(self, sol_diff, neon_diff):
        sol_amount = sol_diff / LAMPORT_PER_SOL
        if neon_diff < 0:
            raise AssertionError(f"NEON has negative difference {neon_diff}")
        # neon_amount = self.web3_client.fromWei(neon_diff, "ether")
        neon_amount = neon_diff / LAMPORT_PER_SOL
        sol_cost = Decimal(sol_amount, DECIMAL_CONTEXT) * Decimal(SOL_PRICE, DECIMAL_CONTEXT)
        neon_cost = Decimal(neon_amount, DECIMAL_CONTEXT) * Decimal(NEON_PRICE, DECIMAL_CONTEXT)
        msg = "Operator receive {:.9f} NEON ({:.2f} $) and spend {:.9f} SOL ({:.2f} $)".format(neon_amount, neon_cost, sol_amount, sol_cost)
        with allure.step(msg):
            assert neon_cost > sol_cost, msg

    def get_compiled_contract(self, name, compiled):
        for key in compiled.keys():
            if key.endswith(name):
                return compiled[key]

    @pytest.fixture(autouse=True)
    def prepare_account(self, prepare_account):
        self.acc = prepare_account

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
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    @pytest.mark.only_stands
    def test_neon_transaction_to_account(self):
        """Verify how many cost neon send to new user"""
        sol_balance_before = self.operator.get_solana_balance()
        acc2 = self.web3_client.create_account()

        neon_balance_before = self.operator.get_neon_balance()
        tx_result = self.web3_client.send_neon(self.acc, acc2, 5)

        assert self.web3_client.get_balance(acc2) == 5
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert sol_balance_before > sol_balance_after, "Operator balance after getBalance doesn't changed"
        assert neon_balance_after > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    @pytest.mark.only_stands
    def test_send_neon_to_exist_account(self):
        """Verify how many cost neon send to use who was already initialized"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()
        acc2 = self.web3_client.create_account()

        assert self.web3_client.get_balance(acc2) == 0

        tx_result = self.web3_client.send_neon(self.acc, acc2, 5)

        assert self.web3_client.get_balance(acc2) == 5

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert sol_balance_before > sol_balance_after, "Operator balance after getBalance doesn't changed"
        assert neon_balance_after > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    @pytest.mark.skip("Not implemented")
    def test_spl_transaction(self):
        pass

    def test_erc20_contract(self):
        """Verify ERC20 token send"""
        #TODO: Add asserts to check cost for deploy big contract
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()
        solcx.install_solc("0.6.6")
        contract_path = (pathlib.Path(__file__).parent / "contracts" / "ERC20.sol").absolute()  # Deploy 331 steps
        compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.6.6")
        contract_interface = self.get_compiled_contract("ERC20", compiled)

        acc2 = self.web3_client.create_account()

        contract_tx = self.web3_client.deploy_contract(
            self.acc,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            gas=10000000,
            constructor_args=[1000],
        )

        contract = self.web3_client.eth.contract(address=contract_tx["contractAddress"], abi=contract_interface["abi"])

        sol_balance_before_request = self.operator.get_solana_balance()

        assert contract.functions.balanceOf(self.acc.address).call() == 1000

        sol_balance_after_request = self.operator.get_solana_balance()
        assert sol_balance_before_request == sol_balance_after_request

        transfer_tx = self.web3_client.send_erc20(
            self.acc, acc2, 500, contract_tx["contractAddress"], abi=contract_interface["abi"]
        )
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert sol_balance_before > sol_balance_after_request > sol_balance_after
        assert neon_balance_after > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_tx_lower_100_instruction(self):
        """Verify we are bill minimum for 100 instruction"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()
        solcx.install_solc("0.8.10")
        contract_path = (pathlib.Path(__file__).parent / "contracts" / "Counter.sol").absolute()  # Deploy 17 steps
        compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.8.10")

        contract_interface = self.get_compiled_contract("Counter", compiled)

        contract_tx = self.web3_client.deploy_contract(
            self.acc,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            gas=10000000,
            constructor_args=[1000],
        )

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert sol_balance_before > sol_balance_after
        assert neon_balance_after > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_contract_get_is_free(self):
        """Verify that get contract calls is free"""
        solcx.install_solc("0.8.10")
        contract_path = (pathlib.Path(__file__).parent / "contracts" / "Counter.sol").absolute()  # Deploy 17 steps
        compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.8.10")

        contract_interface = self.get_compiled_contract("Counter", compiled)

        contract_tx = self.web3_client.deploy_contract(
            self.acc,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            gas=10000000,
            constructor_args=[1000],
        )

        sol_balance_after_deploy = self.operator.get_solana_balance()
        neon_balance_after_deploy = self.operator.get_neon_balance()

        contract = self.web3_client.eth.contract(address=contract_tx["contractAddress"], abi=contract_interface["abi"])
        assert contract.functions.get().call() == 0

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert sol_balance_after_deploy == sol_balance_after
        assert neon_balance_after_deploy == neon_balance_after

    def test_cost_resize_account(self):
        """Verify how much cost account resize"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()
        contract_path = (pathlib.Path(__file__).parent / "contracts" / "Counter.sol").absolute()  # Deploy 17 steps
        compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.8.10")

        contract_interface = self.get_compiled_contract("Counter", compiled)

        contract_tx = self.web3_client.deploy_contract(
            self.acc,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            gas=10000000,
            constructor_args=[1000],
        )

        contract = self.web3_client.eth.contract(address=contract_tx["contractAddress"], abi=contract_interface["abi"])

        sol_balance_before_increase = self.operator.get_solana_balance()

        tx = contract.functions.inc().buildTransaction(
            {"nonce": self.web3_client.eth.get_transaction_count(self.acc.address), "gas": 100000, "gasPrice": 100000}
        )
        tx = self.web3_client.eth.account.sign_transaction(tx, self.acc.key)
        signature = self.web3_client.eth.send_raw_transaction(tx.rawTransaction)
        receipt = self.web3_client.eth.wait_for_transaction_receipt(signature)
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        assert sol_balance_before > sol_balance_before_increase > sol_balance_after
        assert neon_balance_after > neon_balance_before
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_failed_tx(self):
        """Don't get money from user if tx failed"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        acc2 = self.web3_client.create_account()

        balance_user_balance_before = self.web3_client.get_balance(self.acc)

        with pytest.raises(ValueError):
            self.web3_client.send_neon(acc2, self.acc, 5, gas_price=0, gas=0)

        assert self.web3_client.get_balance(self.acc) == balance_user_balance_before

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert neon_balance_after == neon_balance_before
        assert sol_balance_after == sol_balance_before

    @pytest.mark.skip("Not implemented")
    def test_block_deposit(self):
        pass

    @pytest.mark.skip("Not implemented")
    def test_verify_operator_initialization(self):
        pass

    @pytest.mark.skip("Not implemented")
    def test_another_operator_complete_tx(self):
        """Maybe impossible from this side"""

    @pytest.mark.skip("Not implemented")
    def test_send_two_identical_tx(self):
        pass
