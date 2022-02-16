import pathlib
import time
import math
from decimal import Decimal, getcontext

import pytest
import solcx
import allure

from ..base import BaseTests

NEON_PRICE = 0.25

LAMPORT_PER_SOL = 1000000000
DECIMAL_CONTEXT = getcontext()
DECIMAL_CONTEXT.prec = 9

GAS_MULTIPLIER = 1
ETHER_ACCOUNT_SIZE = 256
SPL_ACCOUNT_SIZE = 165
BYTE_COST = 6960


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
        sol_cost = Decimal(sol_amount, DECIMAL_CONTEXT) * Decimal(self.sol_price, DECIMAL_CONTEXT)
        neon_cost = Decimal(neon_amount, DECIMAL_CONTEXT) * Decimal(NEON_PRICE, DECIMAL_CONTEXT)
        msg = "Operator receive {:.9f} NEON ({:.2f} $) and spend {:.9f} SOL ({:.2f} $)".format(
            neon_amount, neon_cost, sol_amount, sol_cost
        )
        print(msg)
        with allure.step(msg):
            assert neon_cost > sol_cost, msg

    @allure.step("Verify operator get full gas for TX")
    def assert_tx_gasused(self, balance_before, transaction):
        gas_price = int(self.web3_client.gas_price() / 1000000000)
        balance = self.operator.get_neon_balance()
        assert transaction["gasUsed"] == transaction["cumulativeGasUsed"]
        assert int((balance - balance_before) / transaction["gasUsed"]) == gas_price

    def get_compiled_contract(self, name, compiled):
        for key in compiled.keys():
            if name in key:
                return compiled[key]

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
        acc2 = self.web3_client.create_account()

        neon_balance_before = self.operator.get_neon_balance()
        tx = self.web3_client.send_neon(self.acc, acc2, 5)

        assert self.web3_client.get_balance(acc2) == 5

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after, "Operator balance after getBalance doesn't changed"
        self.assert_tx_gasused(neon_balance_before, tx)
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
        self.assert_tx_gasused(neon_balance_before, tx)
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

    @pytest.mark.skip("Not implemented")
    def test_spl_transaction(self):
        pass

    def test_erc20_contract(self):
        """Verify ERC20 token send"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        solcx.install_solc("0.6.6")
        contract_path = (pathlib.Path(__file__).parent / "contracts" / "ERC20.sol").absolute()  # Deploy 331 steps, size 4916, tx full size - 4938
        compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.6.6")
        contract_interface = self.get_compiled_contract("ERC20", compiled)

        contract_deploy_tx = self.web3_client.deploy_contract(
            self.acc,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            constructor_args=[1000],
        )

        self.assert_tx_gasused(neon_balance_before, contract_deploy_tx)

        contract = self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

        gas_begin_trx = 331 * GAS_MULTIPLIER
        gas_holder_acc = math.ceil(4938 / 1000) * 331 * GAS_MULTIPLIER
        gas_for_trx = 331 * GAS_MULTIPLIER
        gas_for_space = (ETHER_ACCOUNT_SIZE + SPL_ACCOUNT_SIZE + 4916) * BYTE_COST * GAS_MULTIPLIER
        deploy_cost = gas_for_trx + gas_for_space + gas_holder_acc
        print("Deploy cost ", deploy_cost, contract_deploy_tx["gasUsed"])

        sol_balance_before_request = self.operator.get_solana_balance()
        neon_balance_before_request = self.operator.get_neon_balance()

        # assert neon_balance_before_request == (neon_balance_before + contract_deploy_tx["gasUsed"])

        assert contract.functions.balanceOf(self.acc.address).call() == 1000

        sol_balance_after_request = self.operator.get_solana_balance()
        neon_balance_after_request = self.operator.get_neon_balance()

        assert sol_balance_before_request == sol_balance_after_request
        assert neon_balance_before_request == neon_balance_after_request

        acc2 = self.web3_client.create_account()

        transfer_tx = self.web3_client.send_erc20(
            self.acc, acc2, 500, contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )
        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_after_request > sol_balance_after

        self.assert_tx_gasused(neon_balance_before_request, transfer_tx)
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_tx_lower_100_instruction(self, sol_price):
        """Verify we are bill minimum for 100 instruction"""
        print("START")
        time.sleep(15)
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()
        print(f"SOL Price {sol_price}")
        print(f"Before all SOL {sol_balance_before}  NEON {neon_balance_before}")
        try:
            tx = self.web3_client.send_neon(self.acc, self.web3_client.create_account(), 1, gas=2)
        except:
            pass

        sol_balance_after_tx = self.operator.get_solana_balance()
        neon_balance_after_tx = self.operator.get_neon_balance()
        print(f"After failed tx SOL {sol_balance_after_tx}  NEON {neon_balance_after_tx}")

        solcx.install_solc("0.8.10")
        contract_path = (pathlib.Path(__file__).parent / "contracts" / "Counter.sol").absolute()  # Deploy 17 steps
        compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.8.10")

        contract_interface = self.get_compiled_contract("Counter", compiled)

        contract_deploy_tx = self.web3_client.deploy_contract(
            self.acc,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
        )

        # contract = self.web3_client.eth.contract(
        #     address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        # )
        #
        # sol_balance_after_deploy = self.operator.get_solana_balance()
        # neon_balance_after_deploy = self.operator.get_neon_balance()
        # print("gas used: ", contract_deploy_tx["gasUsed"])
        # assert neon_balance_after_deploy == (neon_balance_before + contract_deploy_tx["gasUsed"])

        # inc_tx = contract.functions.inc().buildTransaction(
        #     {
        #         "from": self.acc.address,
        #         "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
        #         "gasPrice": self.web3_client.gas_price(),
        #     }
        # )
        #
        # inc_tx["gas"] = self.web3_client._web3.eth.estimate_gas(inc_tx)
        # print(f"INC transaction gas {inc_tx['gas']} and gasPrice {inc_tx['gasPrice']}")
        # inc_tx = self.web3_client.eth.account.sign_transaction(inc_tx, self.acc.key)
        # signature = self.web3_client.eth.send_raw_transaction(inc_tx.rawTransaction)
        # inc_receipt = self.web3_client.eth.wait_for_transaction_receipt(signature)
        #
        # assert contract.functions.get().call() == 1

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()
        print(f"After deploy SOL {sol_balance_after}  NEON {neon_balance_after}")
        print("Deploy tx ", contract_deploy_tx)
        # assert sol_balance_before > sol_balance_after_deploy > sol_balance_after
        # assert neon_balance_after == (neon_balance_after_deploy + inc_receipt["gasUsed"])
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
        )

        sol_balance_after_deploy = self.operator.get_solana_balance()
        neon_balance_after_deploy = self.operator.get_neon_balance()

        contract = self.web3_client.eth.contract(address=contract_tx["contractAddress"], abi=contract_interface["abi"])

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
        contract_path = (
            pathlib.Path(__file__).parent / "contracts" / "IncreaseStorage.sol"
        ).absolute()  # Deploy 17 steps
        compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.8.10")

        contract_interface = self.get_compiled_contract("IncreaseStorage", compiled)

        contract_tx = self.web3_client.deploy_contract(
            self.acc,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
        )
        self.assert_tx_gasused(neon_balance_before, contract_tx)
        contract = self.web3_client.eth.contract(address=contract_tx["contractAddress"], abi=contract_interface["abi"])

        sol_balance_before_increase = self.operator.get_solana_balance()
        neon_balance_before_increase = self.operator.get_neon_balance()

        inc_tx = contract.functions.inc().buildTransaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        inc_tx["gas"] = self.web3_client._web3.eth.estimate_gas(inc_tx)

        inc_tx = self.web3_client.eth.account.sign_transaction(inc_tx, self.acc.key)
        signature = self.web3_client.eth.send_raw_transaction(inc_tx.rawTransaction)
        increase_tx = self.web3_client.eth.wait_for_transaction_receipt(signature)

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert sol_balance_before > sol_balance_before_increase > sol_balance_after, "SOL Balance not changed"
        assert neon_balance_after > neon_balance_before_increase > neon_balance_before, "NEON Balance incorrect"
        self.assert_tx_gasused(neon_balance_before_increase, increase_tx)
        self.assert_profit(sol_balance_before - sol_balance_after, neon_balance_after - neon_balance_before)

    def test_failed_tx(self):
        """Don't get money from user if tx failed"""
        sol_balance_before = self.operator.get_solana_balance()
        neon_balance_before = self.operator.get_neon_balance()

        acc2 = self.web3_client.create_account()

        balance_user_balance_before = self.web3_client.get_balance(self.acc)

        with pytest.raises(ValueError, match=r"Transaction simulation failed.*") as e:
            self.web3_client.send_neon(self.acc, acc2, 5, gas=1)

        assert self.web3_client.get_balance(self.acc) == balance_user_balance_before

        sol_balance_after = self.operator.get_solana_balance()
        neon_balance_after = self.operator.get_neon_balance()

        assert neon_balance_after == neon_balance_before
        assert sol_balance_after == sol_balance_before

