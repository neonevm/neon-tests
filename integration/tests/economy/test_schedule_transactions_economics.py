import allure
import pytest

from utils.consts import LAMPORT_TO_INNER_SOL
from utils.helpers import wait_condition, decode_function_signature
from utils.neon_user import NeonUser
from utils.scheduled_trx import CreateTreeAccMultipleData, ScheduledTrxEstimateRequest
from utils.scheduled_trx import ScheduledTransaction
from utils.web3client import BASE_MAX_PRIORITY_FEE
from .steps import (
    assert_profit,
    check_alt_off,
    calculate_additional_expenses,
)
from .test_economics import sum_balances

from ..basic.helpers.rpc_checks import check_trx_is_success


@allure.story("Operator economy")
class TestScheduledTransactionEconomics:

    @pytest.mark.only_stands
    @pytest.mark.parametrize("is_dependent", [True, False])
    def test_multiple_scheduled_trx_sols_outside_neon(
        self,
        operator,
        web3_client_sol,
        neon_user_func_scope,
        increase_storage_contract,
        evm_loader,
        treasury_pool,
        sol_price,
        is_dependent,
        sol_client,
    ):
        neon_user = neon_user_func_scope
        evm_loader.create_balance_account(neon_user.neon_address, neon_user.solana_account, evm_loader.sol_chain_id)

        trx_count = 4
        data = decode_function_signature("incWithoutALT()")

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)

        user_inner_sol_balance_before = web3_client_sol.get_balance(neon_user.checksum_address)
        user_outer_sol_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())

        tokens_volume_before = (
            token_balance_before
            + user_inner_sol_balance_before
            + (user_outer_sol_balance_before * LAMPORT_TO_INNER_SOL)
        )

        trx_estimate_obj_list = []
        for i in range(trx_count):
            child_transaction = None if is_dependent else "0xFFFF"
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user.checksum_address,
                    increase_storage_contract.address,
                    data,
                    child_transaction=child_transaction,
                )
            )

        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        for i in range(trx_count):
            child_transaction = i + 1 if is_dependent and i != trx_count - 1 else 0xFFFF
            success_limit = 1 if is_dependent and i != 0 else 0
            tree_acc_data.add_trx(trxs[i], child_transaction, success_limit)

        tree_acc = evm_loader.create_tree_account_multiple(
            neon_user,
            treasury_pool,
            tree_acc_data.data,
        )

        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)
            receipt = web3_client_sol.wait_for_transaction_receipt(trx.hash().hex(), timeout=120)
            check_alt_off(web3_client_sol, sol_client, receipt)

        wait_condition(lambda: not evm_loader.account_exists(tree_acc), timeout_sec=120, delay=2)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)

        user_inner_sol_balance_after = web3_client_sol.get_balance(neon_user.checksum_address)
        user_outer_sol_balance_after = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
        new_token_volume = (
            +user_inner_sol_balance_after + token_balance_after + (user_outer_sol_balance_after * LAMPORT_TO_INNER_SOL)
        )

        additional_expected_spending = calculate_additional_expenses(trx_count)
        diff_volume = tokens_volume_before - (new_token_volume + additional_expected_spending)
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_multiple_scheduled_trx_sols_inside_neon(
        self,
        operator,
        web3_client_sol,
        increase_storage_contract,
        evm_loader,
        treasury_pool,
        sol_price,
        neon_user_with_sols_inside_neon,
        sol_client,
    ):
        evm_loader.create_balance_account(
            neon_user_with_sols_inside_neon.neon_address,
            neon_user_with_sols_inside_neon.solana_account,
            evm_loader.sol_chain_id,
        )

        trx_count = 4
        data = decode_function_signature("incWithoutALT()")

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)
        tokens_volume_before = sum_balances(web3_client_sol, operator, neon_user_with_sols_inside_neon)

        trx_estimate_obj_list = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user_with_sols_inside_neon.checksum_address,
                    increase_storage_contract.address,
                    data,
                    child_transaction="0xFFFF",
                )
            )
        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user_with_sols_inside_neon.solana_account.pubkey(), trx_estimate_obj_list
        )
        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        for i in range(trx_count):
            child_transaction = 0xFFFF
            success_limit = 0
            tree_acc_data.add_trx(trxs[i], child_transaction, success_limit)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user_with_sols_inside_neon,
            treasury_pool,
            tree_acc_data.data,
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)
            receipt = web3_client_sol.wait_for_transaction_receipt(trx.hash().hex(), timeout=120)
            check_alt_off(web3_client_sol, sol_client, receipt)
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)

        tokens_volume_after = sum_balances(web3_client_sol, operator, neon_user_with_sols_inside_neon)
        diff_volume = tokens_volume_before - tokens_volume_after
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_multiple_scheduled_trx_with_failed_trx(
        self,
        web3_client_sol,
        neon_user_func_scope,
        treasury_pool,
        revert_contract_caller,
        evm_loader,
        operator,
        sol_price,
        sol_client,
    ):
        neon_user = neon_user_func_scope
        evm_loader.create_balance_account(neon_user.neon_address, neon_user.solana_account, evm_loader.sol_chain_id)

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)
        user_inner_sol_balance_before = web3_client_sol.get_balance(neon_user.checksum_address)
        user_outer_sol_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())

        tokens_volume_before = (
            token_balance_before
            + user_inner_sol_balance_before
            + (user_outer_sol_balance_before * LAMPORT_TO_INNER_SOL)
        )

        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
        gas_limit = 30000000

        call_data_trx0 = decode_function_signature("doAssert()")
        call_data_trx1 = decode_function_signature("indexedArgs()")

        trxs = []
        for i, call_data in enumerate([call_data_trx0, call_data_trx1]):
            trxs.append(
                ScheduledTransaction(
                    neon_user.neon_address,
                    None,
                    nonce,
                    index=i,
                    target=revert_contract_caller.address,
                    call_data=call_data,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                    gas_limit=gas_limit,
                    chain_id=web3_client_sol.chain_id,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(trxs[0], 1, 0)
        tree_acc_data.add_trx(trxs[1], 0xFFFF, 1)

        tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)
        web3_client_sol.send_all_scheduled_transactions(trxs)
        receipt = web3_client_sol.wait_for_transaction_receipt(trxs[1].hash(), timeout=180)
        assert receipt["status"] == 0
        wait_condition(lambda: not evm_loader.account_exists(tree_acc), timeout_sec=120, delay=2)
        check_alt_off(web3_client_sol, sol_client, receipt)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)

        trx_count = 2
        user_inner_sol_balance_after = web3_client_sol.get_balance(neon_user.checksum_address)
        user_outer_sol_balance_after = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
        new_token_volume = (
            +user_inner_sol_balance_after + token_balance_after + (user_outer_sol_balance_after * LAMPORT_TO_INNER_SOL)
        )

        additional_expected_spending = calculate_additional_expenses(trx_count)

        diff_volume = tokens_volume_before - (new_token_volume + additional_expected_spending)
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_scheduled_trx_for_erc20_for_spl_inside_sols(
        self,
        web3_client_sol,
        neon_user_with_sols_inside_neon,
        erc20_spl_mintable,
        evm_loader,
        treasury_pool,
        operator,
        sol_price,
        sol_client,
    ):
        evm_loader.create_balance_account(
            neon_user_with_sols_inside_neon.neon_address,
            neon_user_with_sols_inside_neon.solana_account,
            evm_loader.sol_chain_id,
        )
        erc20_spl_mintable.approve(erc20_spl_mintable.owner, neon_user_with_sols_inside_neon.checksum_address, 800)
        operator_inner_balance_before = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_before = operator.get_solana_balance()
        user_inner_sol_balance_b = web3_client_sol.get_balance(neon_user_with_sols_inside_neon.checksum_address)

        recipient = NeonUser(evm_loader.loader_id)
        recipient_balance_before = web3_client_sol.get_balance(recipient.checksum_address)
        tokens_volume_before = operator_inner_balance_before + user_inner_sol_balance_b + recipient_balance_before

        top_up_in_trx = 400
        amount_to_recipient = 400
        data_0 = data_1 = decode_function_signature(
            "transferFrom(address,address,uint256)",
            [erc20_spl_mintable.owner.address, neon_user_with_sols_inside_neon.checksum_address, top_up_in_trx],
        )
        data_2 = data_3 = decode_function_signature(
            "transfer(address,uint256)", [recipient.checksum_address, amount_to_recipient]
        )

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address,
            erc20_spl_mintable.address,
            data_0,
            child_transaction=hex(2),
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address,
            erc20_spl_mintable.address,
            data_1,
            child_transaction=hex(3),
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address,
            erc20_spl_mintable.address,
            data_2,
            child_transaction="0xFFFF",
        )
        trx_estimate_3 = ScheduledTrxEstimateRequest(
            neon_user_with_sols_inside_neon.checksum_address,
            erc20_spl_mintable.address,
            data_3,
            child_transaction="0xFFFF",
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]

        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user_with_sols_inside_neon.solana_account.pubkey(), trx_estimate_obj_list
        )

        trxs = []
        for i in range(len(trx_estimate_obj_list)):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user_with_sols_inside_neon, treasury_pool, tree_acc_data.data
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)
            receipt = web3_client_sol.wait_for_transaction_receipt(trx.hash().hex(), timeout=120)
            check_alt_off(web3_client_sol, sol_client, receipt)
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

        operator_inner_balance_after = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_after = operator.get_solana_balance()

        user_inner_sol_balance_after = web3_client_sol.get_balance(neon_user_with_sols_inside_neon.checksum_address)
        recipient_balance_after = web3_client_sol.get_balance(recipient.checksum_address)
        tokens_volume_after = operator_inner_balance_after + user_inner_sol_balance_after + recipient_balance_after

        diff_volume = tokens_volume_before - tokens_volume_after
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = operator_sol_balance_before - operator_sol_balance_after
        token_diff = web3_client_sol.to_main_currency(operator_inner_balance_after - operator_inner_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_scheduled_trx_for_erc20_for_spl_outside_sols(
        self,
        web3_client_sol,
        neon_user_func_scope,
        erc20_spl_mintable,
        evm_loader,
        treasury_pool,
        operator,
        sol_price,
        sol_client,
    ):
        neon_user = neon_user_func_scope
        evm_loader.create_balance_account(neon_user.neon_address, neon_user.solana_account, evm_loader.sol_chain_id)
        erc20_spl_mintable.approve(erc20_spl_mintable.owner, neon_user.checksum_address, 800)

        operator_inner_balance_before = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_before = operator.get_solana_balance()

        recipient = NeonUser(evm_loader.loader_id)
        recipient_balance_before = web3_client_sol.get_balance(recipient.checksum_address)

        user_inner_sol_balance_before = web3_client_sol.get_balance(neon_user.checksum_address)
        user_outer_sol_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
        tokens_volume_before = (
            operator_inner_balance_before
            + user_inner_sol_balance_before
            + recipient_balance_before
            + (user_outer_sol_balance_before * LAMPORT_TO_INNER_SOL)
        )

        top_up_in_trx = 400
        amount_to_recipient = 400
        data_0 = data_1 = decode_function_signature(
            "transferFrom(address,address,uint256)",
            [erc20_spl_mintable.owner.address, neon_user.checksum_address, top_up_in_trx],
        )
        data_2 = data_3 = decode_function_signature(
            "transfer(address,uint256)", [recipient.checksum_address, amount_to_recipient]
        )

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_0, child_transaction=hex(2)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_1, child_transaction=hex(3)
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_2, child_transaction="0xFFFF"
        )
        trx_estimate_3 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_3, child_transaction="0xFFFF"
        )
        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1, trx_estimate_2, trx_estimate_3]

        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)

        trxs = []
        for i in range(len(trx_estimate_obj_list)):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)

        tree_account = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=180)
            receipt = web3_client_sol.wait_for_transaction_receipt(trx.hash().hex(), timeout=120)
            check_alt_off(web3_client_sol, sol_client, receipt)
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

        operator_inner_balance_after = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_after = operator.get_solana_balance()

        trx_count = 4
        user_inner_sol_balance_after = web3_client_sol.get_balance(neon_user.checksum_address)
        user_outer_sol_balance_after = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
        recipient_balance_after = web3_client_sol.get_balance(recipient.checksum_address)
        new_token_volume = (
            user_inner_sol_balance_after
            + operator_inner_balance_after
            + recipient_balance_after
            + (user_outer_sol_balance_after * LAMPORT_TO_INNER_SOL)
        )

        additional_expected_spending = calculate_additional_expenses(trx_count)

        diff_volume = tokens_volume_before - (new_token_volume + additional_expected_spending)
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = operator_sol_balance_before - operator_sol_balance_after
        token_diff = web3_client_sol.to_main_currency(operator_inner_balance_after - operator_inner_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_scheduled_trx_send_value(
        self,
        web3_client_sol,
        evm_loader,
        treasury_pool,
        operator,
        sol_price,
        event_caller_sol_chain,
        neon_user_with_sols_inside_neon,
    ):
        user = neon_user_with_sols_inside_neon
        evm_loader.create_balance_account(
            user.neon_address,
            user.solana_account,
            evm_loader.sol_chain_id,
        )
        operator_inner_balance_before = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_before = operator.get_solana_balance()

        tokens_volume_before = sum_balances(web3_client_sol, operator, user, event_caller_sol_chain)
        call_data = decode_function_signature("indexedArgs()")
        value = 10000
        trx_estimate_obj = ScheduledTrxEstimateRequest(
            user.checksum_address, event_caller_sol_chain.address, call_data, value=value
        )
        estimate_result = web3_client_sol.estimate_scheduled(user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(tx, 0xFFFF, 0)
        tree_account = evm_loader.create_tree_account_multiple(user, treasury_pool, tree_acc_data.data)
        web3_client_sol.send_scheduled_transaction(tx)
        web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)
        check_trx_is_success(web3_client_sol, evm_loader, tx.hash().hex(), timeout=180)
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

        operator_inner_balance_after = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_after = operator.get_solana_balance()

        tokens_volume_after = sum_balances(web3_client_sol, operator, user, event_caller_sol_chain)

        diff_volume = tokens_volume_before - tokens_volume_after
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = operator_sol_balance_before - operator_sol_balance_after
        token_diff = web3_client_sol.to_main_currency(operator_inner_balance_after - operator_inner_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_user_has_not_enough_sol_for_trx_inside_neon(
        self, evm_loader, neon_user_func_scope, web3_client_sol, common_contract, treasury_pool, operator, sol_price
    ):
        user = neon_user_func_scope
        evm_loader.create_balance_account(
            user.neon_address,
            user.solana_account,
            evm_loader.sol_chain_id,
        )
        operator_inner_balance_before = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_before = operator.get_solana_balance()

        contract_data = 18
        data = decode_function_signature("setNumber(uint256)", [contract_data])
        trx_estimate_obj = ScheduledTrxEstimateRequest(user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(user.solana_account.pubkey(), [trx_estimate_obj])
        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        lamports = 999
        evm_loader.deposit_wrapped_sol_from_solana_to_neon(
            user.solana_account,
            user.checksum_address,
            int(lamports),
        )

        user_inner_sol_balance_before = web3_client_sol.get_balance(user.checksum_address)
        user_outer_sol_balance_before = evm_loader.get_solana_balance(user.solana_account.pubkey())

        tokens_volume_before = (
            operator_inner_balance_before
            + user_inner_sol_balance_before
            + (user_outer_sol_balance_before * LAMPORT_TO_INNER_SOL)
        )

        user_outer_sol_balance_before_send_tx = evm_loader.get_solana_balance(user.solana_account.pubkey())
        tree_account = evm_loader.create_tree_account(user, treasury_pool, tx.encode())
        web3_client_sol.send_scheduled_transaction(tx)
        check_trx_is_success(web3_client_sol, evm_loader, tx.hash().hex())
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

        operator_inner_balance_after = operator.get_token_balance(web3_client_sol)
        operator_sol_balance_after = operator.get_solana_balance()
        user_inner_sol_balance_after = web3_client_sol.get_balance(user.checksum_address)
        user_outer_sol_balance_after = evm_loader.get_solana_balance(user.solana_account.pubkey())

        tokens_volume_after = (
            operator_inner_balance_after
            + user_inner_sol_balance_after
            + (user_outer_sol_balance_after * LAMPORT_TO_INNER_SOL)
        )

        additional_expenses = calculate_additional_expenses(trx_count=1)

        # we need to sure that user have not enough sols in neon and use outer sol balance
        diff = user_outer_sol_balance_before_send_tx - (
            user_outer_sol_balance_after + (additional_expenses / LAMPORT_TO_INNER_SOL)
        )
        assert diff > 0, f"Expected that user spent lamports from outer balance, but diff = {0}"

        diff_volume = tokens_volume_before - tokens_volume_after - additional_expenses
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = operator_sol_balance_before - operator_sol_balance_after
        token_diff = web3_client_sol.to_main_currency(operator_inner_balance_after - operator_inner_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)

    def test_iteration_scheduled_trx_failed(
        self,
        web3_client_sol,
        neon_user_func_scope,
        treasury_pool,
        revert_contract_caller,
        common_contract,
        evm_loader,
        operator,
        sol_price,
        sol_client,
    ):
        user = neon_user_func_scope
        evm_loader.create_balance_account(user.neon_address, user.solana_account, evm_loader.sol_chain_id)

        sol_balance_before = operator.get_solana_balance()
        token_balance_before = operator.get_token_balance(web3_client_sol)

        trx_count = 2
        contract_data = 18
        data = decode_function_signature("setNumber(uint256)", [contract_data])
        nonce = web3_client_sol.get_nonce(user.checksum_address)
        trx_estimate_obj_list = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    user.checksum_address,
                    common_contract.address,
                    data,
                )
            )
        estimate_result = web3_client_sol.estimate_scheduled(user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        call_data = decode_function_signature("doTrivialRevertAferIterativeActions()")
        tx1 = ScheduledTransaction(
            user.neon_address,
            None,
            nonce,
            index=2,
            target=revert_contract_caller.address,
            value=0,
            call_data=call_data,
            chain_id=evm_loader.sol_chain_id,
            max_fee_per_gas=trxs[0].max_fee_per_gas,
            max_priority_fee_per_gas=trxs[0].max_priority_fee_per_gas,
        )
        trxs.append(tx1)

        user_inner_sol_balance_before = web3_client_sol.get_balance(user.checksum_address)
        user_outer_sol_balance_before = evm_loader.get_solana_balance(user.solana_account.pubkey())

        tokens_volume_before = (
            token_balance_before
            + user_inner_sol_balance_before
            + (user_outer_sol_balance_before * LAMPORT_TO_INNER_SOL)
        )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 1, 0)
        tree_acc_data.add_trx(trxs[1], 2, 1)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)

        tree_acc = evm_loader.create_tree_account_multiple(user, treasury_pool, tree_acc_data.data)

        web3_client_sol.send_all_scheduled_transactions(trxs)
        receipt = web3_client_sol.wait_for_transaction_receipt(trxs[-1].hash(), timeout=180)
        wait_condition(lambda: not evm_loader.account_exists(tree_acc), timeout_sec=120, delay=2)
        check_alt_off(web3_client_sol, sol_client, receipt)

        sol_balance_after = operator.get_solana_balance()
        token_balance_after = operator.get_token_balance(web3_client_sol)

        user_inner_sol_balance_after = web3_client_sol.get_balance(user.checksum_address)
        user_outer_sol_balance_after = evm_loader.get_solana_balance(user.solana_account.pubkey())

        new_token_volume = (
            +user_inner_sol_balance_after + token_balance_after + (user_outer_sol_balance_after * LAMPORT_TO_INNER_SOL)
        )

        trx_count = 3
        additional_expected_spending = calculate_additional_expenses(trx_count)

        diff_volume = tokens_volume_before - (new_token_volume + additional_expected_spending)
        assert diff_volume == 0, f"tokens volume not same, diff={diff_volume}"

        token_price = web3_client_sol.get_token_usd_gas_price()
        sol_diff = sol_balance_before - sol_balance_after
        token_diff = web3_client_sol.to_main_currency(token_balance_after - token_balance_before)
        assert_profit(sol_diff, sol_price, token_diff, token_price, web3_client_sol.native_token_name)
