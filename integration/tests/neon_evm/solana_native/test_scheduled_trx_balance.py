import eth_abi
import pytest
from eth_utils import abi

from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.contract import get_contract_bin
from integration.tests.neon_evm.utils.ethereum import create_contract_address
from utils.consts import (
    LAMPORT_PER_SOL,
    TRX_EXECUTION_PRICE,
    PAYMENT_FOR_TREE_ACCOUNT_DELETING,
    LAMPORT_TO_INNER_SOL,
    OPERATOR_FEE_TO_NEON,
    TREE_ACCOUNT_BALANCE_STRUCT_ENLARGEMENT_COST,
    PAYMENT_FOR_TRX_FINISHING,
)
from utils.helpers import decode_function_signature
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData
from utils.solana_logs_helper import get_total_gas_used

from utils.types import Contract


# Test should be fixed after NDEV-3838
def test_successful_single_trx_with_outer_deposit(
    neon_user, evm_loader, operator_keypair, treasury_pool, basic_contract, neon_api_client, holder_acc
):
    # trx_status: successful
    # user_balance: only outer deposit
    # tree_acc: one schd trx in tree acc

    trx_count = 1
    iter_per_trx = 2

    evm_loader.create_balance_account(neon_user.checksum_address, neon_user.solana_account, evm_loader.sol_chain_id)

    operator_balance_initial_inner = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_initial_outer = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_initial_outer = evm_loader.get_solana_balance(treasury_pool.account)

    nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
    call_data = decode_function_signature("setNumber(uint256)", args=[10])

    tx_0 = ScheduledTransaction(
        neon_user.neon_address,
        None,
        nonce,
        0,
        target=basic_contract.eth_address,
        value=0,
        call_data=call_data,
        chain_id=evm_loader.sol_chain_id,
    )
    tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
    tree_acc_data.add_trx(tx_0, 0xFFFF, 0)
    tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    neon_user_balance_after_tree_created_outer = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    neon_user_balance_diff = neon_user_balance_initial_outer - neon_user_balance_after_tree_created_outer
    estimated_trx_cost = tx_0.gas_limit * tx_0.max_fee_per_gas
    neon_user_additional_payments = (
        PAYMENT_FOR_TREE_ACCOUNT_DELETING  # + PAYMENT_FOR_TRX_FINISHING * trx_count  # uncomment after fix NDEV-3838
    )
    expected_neon_user_balance_diff = (
        estimated_trx_cost / LAMPORT_TO_INNER_SOL
        + neon_user_additional_payments
        + TRX_EXECUTION_PRICE
        + TREE_ACCOUNT_BALANCE_STRUCT_ENLARGEMENT_COST
    )

    assert (
        neon_user_balance_diff == expected_neon_user_balance_diff
    ), f"Balance has been changed more than expected. Delta {expected_neon_user_balance_diff - neon_user_balance_diff}"

    treasury_pool_balance_after_tree_created_outer = evm_loader.get_solana_balance(treasury_pool.account)
    delta_treasury_balance = treasury_pool_balance_initial_outer - treasury_pool_balance_after_tree_created_outer

    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    expected_tree_acc_balance = delta_treasury_balance + neon_user_additional_payments
    assert (
        tree_acc_balance == expected_tree_acc_balance
    ), f"Tree acc balance failed, delta {expected_tree_acc_balance - tree_acc_balance}"

    tree_acc_balance_inner = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance
    assert (
        tree_acc_balance_inner == estimated_trx_cost
    ), f"Tree acc inner balance failed, actual {tree_acc_balance_inner}"

    additional_accounts = [
        basic_contract.solana_address,
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]

    resp = evm_loader.execute_scheduled_trx_from_instruction(
        tx_0,
        operator_keypair,
        holder_acc,
        tree_acc,
        treasury_pool,
        additional_accounts,
    )
    gas_used_exec = get_total_gas_used(resp)

    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)
    operator_balance_trx_finished_inner = evm_loader.get_operator_neon_balance(
        operator_keypair, evm_loader.sol_chain_id
    )
    exec_trx_cost = gas_used_exec * tx_0.max_fee_per_gas

    expected_neon_operator_balance = (
        operator_balance_initial_inner + exec_trx_cost + PAYMENT_FOR_TRX_FINISHING * trx_count
    )
    # expected_neon_operator_balance = operator_balance_initial_inner + exec_trx_cost #uncomment after fix NDEV-3838

    assert (
        operator_balance_trx_finished_inner == expected_neon_operator_balance
    ), f"Operator balance failed. Diff {operator_balance_trx_finished_inner - expected_neon_operator_balance}"
    operator_balance_before_tree_destroyed_outer = evm_loader.get_solana_balance(operator_keypair.pubkey())
    evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_acc)
    neon_user_balance_tree_destroyed_inner = evm_loader.get_neon_balance(
        neon_user.neon_address, evm_loader.sol_chain_id
    )
    treasury_pool_balance_tree_destroyed_outer = evm_loader.get_solana_balance(treasury_pool.account)
    operator_balance_after_tree_destroyed_outer = evm_loader.get_solana_balance(operator_keypair.pubkey())
    expected_operator_balance_after_tree_destroyed_outer = (
        operator_balance_before_tree_destroyed_outer
        - TRX_EXECUTION_PRICE
        + OPERATOR_FEE_TO_NEON * iter_per_trx * trx_count
    )
    assert operator_balance_after_tree_destroyed_outer == expected_operator_balance_after_tree_destroyed_outer, (
        f"Operator balance is failed. Expected {expected_operator_balance_after_tree_destroyed_outer}, "
        f"DElta {expected_operator_balance_after_tree_destroyed_outer - operator_balance_after_tree_destroyed_outer}",
    )

    expected_treasury_pool_balance_tree_destroyed_outer = (
        treasury_pool_balance_initial_outer + OPERATOR_FEE_TO_NEON * iter_per_trx * trx_count
    )
    assert treasury_pool_balance_tree_destroyed_outer == expected_treasury_pool_balance_tree_destroyed_outer, (
        f"Treasury pool balance is failed. Expected {treasury_pool_balance_initial_outer}, but got {treasury_pool_balance_after_tree_created_outer}"
        f"DELTA {treasury_pool_balance_initial_outer - expected_treasury_pool_balance_tree_destroyed_outer}"
    )
    expected_neon_user_balance_remainder_inner = estimated_trx_cost - exec_trx_cost

    assert neon_user_balance_tree_destroyed_inner == expected_neon_user_balance_remainder_inner, (
        f"Expected {expected_neon_user_balance_remainder_inner}, but got {neon_user_balance_tree_destroyed_inner}, "
        f"Delta {(neon_user_balance_tree_destroyed_inner - expected_neon_user_balance_remainder_inner)}"
    )


@pytest.mark.skip(reason="NDEV-3838")
def test_success_two_trx_with_inner_deposit(
    neon_user, neon_api_client, evm_loader, operator_keypair, treasury_pool, basic_contract, solana_account, holder_acc
):

    # trx_status: success
    # user_balance: inner deposit non zero
    # tree_acc: two scheduled trx in tree acc

    trx_count = 2
    iter_per_trx = 2
    gas_limit = 30_000_000
    max_fee_per_gas = 3_000_000_000

    evm_loader.create_balance_account(neon_user.checksum_address, neon_user.solana_account, evm_loader.sol_chain_id)
    evm_loader.deposit_wrapped_sol_from_solana_to_neon(
        neon_user.solana_account,
        "0x" + neon_user.neon_address.hex(),
        int(1 * LAMPORT_PER_SOL),
    )

    operator_balance_initial_inner = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_initial_outer = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    neon_user_balance_initial_inner = evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id)
    treasury_pool_balance_initial_outer = evm_loader.get_solana_balance(treasury_pool.account)

    nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
    contract_code = (
        get_contract_bin("common/Common", contract_name="CommonCaller", version="0.8.12")
        + eth_abi.encode(["address"], [basic_contract.eth_address.hex()]).hex()
    )
    caller_contract: Contract = create_contract_address(neon_user.neon_address, evm_loader)

    emulate_deploy = neon_api_client.emulate(
        neon_user.neon_address.hex(),
        contract=None,
        data=contract_code,
        chain_id=evm_loader.sol_chain_id,
    )
    additional_accounts_deploy = [Pubkey.from_string(item["pubkey"]) for item in emulate_deploy["solana_accounts"]]

    data_call = abi.function_signature_to_4byte_selector("getNumber()")
    tx0 = ScheduledTransaction(
        neon_user.neon_address,
        None,
        nonce,
        index=0,
        call_data=bytes.fromhex(contract_code),
        max_fee_per_gas=max_fee_per_gas,
        max_priority_fee_per_gas=2_500_000_000,
        gas_limit=gas_limit,
        target=None,
        chain_id=evm_loader.sol_chain_id,
    )
    tx1 = ScheduledTransaction(
        neon_user.neon_address,
        None,
        nonce,
        index=1,
        target=caller_contract.eth_address,
        max_fee_per_gas=max_fee_per_gas,
        max_priority_fee_per_gas=2_500_000_000,
        gas_limit=gas_limit,
        call_data=data_call,
        chain_id=evm_loader.sol_chain_id,
    )

    tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
    tree_acc_data.add_trx(tx0, 1, 0)
    tree_acc_data.add_trx(tx1, 0xFFFF, 1)

    tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    operator_balance_after_tree_created_inner = evm_loader.get_operator_neon_balance(
        operator_keypair, evm_loader.sol_chain_id
    )
    assert (
        operator_balance_initial_inner == operator_balance_after_tree_created_inner
    ), "Operator balance has changed, but is not supposed to"

    neon_user_balance_after_tree_created_outer = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    neon_user_balance_after_tree_created_inner = evm_loader.get_neon_balance(
        neon_user.neon_address, evm_loader.sol_chain_id
    )
    neon_user_balance_diff_outer = neon_user_balance_initial_outer - neon_user_balance_after_tree_created_outer
    neon_user_balance_diff_inner = neon_user_balance_initial_inner - neon_user_balance_after_tree_created_inner
    estimated_trx_cost = gas_limit * max_fee_per_gas
    neon_user_additional_payments = PAYMENT_FOR_TREE_ACCOUNT_DELETING + PAYMENT_FOR_TRX_FINISHING * trx_count  # NDEV-
    expected_neon_user_balance_diff = (
        +neon_user_additional_payments + TRX_EXECUTION_PRICE + TREE_ACCOUNT_BALANCE_STRUCT_ENLARGEMENT_COST
    )
    assert (
        neon_user_balance_diff_outer == expected_neon_user_balance_diff
    ), f"Balance has been changed more than expected. Delta {neon_user_balance_diff_outer}"

    expected_inner_delta = estimated_trx_cost * trx_count
    assert (
        neon_user_balance_diff_inner == expected_inner_delta
    ), f"Inner balance is failed. Delta before/after tree acc creation {neon_user_balance_diff_inner}"
    treasury_pool_balance_after_tree_created_outer = evm_loader.get_solana_balance(treasury_pool.account)
    delta_treasury_balance = treasury_pool_balance_initial_outer - treasury_pool_balance_after_tree_created_outer

    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    assert (
        tree_acc_balance == delta_treasury_balance + neon_user_additional_payments
    ), f"Tree acc balance failed, actual {tree_acc_balance}"

    tree_acc_balance_inner = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance
    assert (
        tree_acc_balance_inner == estimated_trx_cost * trx_count
    ), f"Tree acc inner balance failed, actual {tree_acc_balance_inner}"
    neon_user_inner_balance_after_tree = evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id)

    additional_accounts_call = [
        caller_contract.solana_address,
        basic_contract.solana_address,
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]
    evm_loader.write_transaction_to_holder_account(tx0.encode(), holder_acc, operator_keypair)
    resp_tx0 = evm_loader.execute_scheduled_trx_from_instruction(
        tx0,
        operator_keypair,
        holder_acc,
        tree_acc,
        treasury_pool,
        additional_accounts_deploy,
    )
    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)

    resp_tx1 = evm_loader.execute_scheduled_trx_from_instruction(
        tx1, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts_call
    )
    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)

    exec_trx_cost = (get_total_gas_used(resp_tx0) + get_total_gas_used(resp_tx1)) * max_fee_per_gas

    operator_balance_trxs_finished_inner = evm_loader.get_operator_neon_balance(
        operator_keypair, evm_loader.sol_chain_id
    )

    expected_operator_balance = operator_balance_initial_inner + exec_trx_cost
    assert (
        operator_balance_trxs_finished_inner == expected_operator_balance
    ), f"Operator balance failed. Diff {operator_balance_trxs_finished_inner - expected_operator_balance}"

    evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_acc)

    neon_user_inner_balance_tree_destroyed = evm_loader.get_neon_balance(
        neon_user.neon_address, evm_loader.sol_chain_id
    )
    treasury_pool_balance_tree_destroyed = evm_loader.get_solana_balance(treasury_pool.account)

    expected_neon_user_balance_remainder = (
        neon_user_inner_balance_after_tree + estimated_trx_cost * trx_count - exec_trx_cost
    )
    assert neon_user_inner_balance_tree_destroyed == expected_neon_user_balance_remainder, (
        f"Expected {expected_neon_user_balance_remainder}, but got {neon_user_inner_balance_tree_destroyed},"
        f"Delta {(neon_user_inner_balance_tree_destroyed - expected_neon_user_balance_remainder) / LAMPORT_TO_INNER_SOL}"
    )
    expected_treasury_pool_balance = (
        treasury_pool_balance_initial_outer + OPERATOR_FEE_TO_NEON * iter_per_trx * trx_count
    )
    assert treasury_pool_balance_tree_destroyed == expected_treasury_pool_balance, (
        f"Treasury pool balance is failed. "
        f"DELTA {treasury_pool_balance_initial_outer - expected_treasury_pool_balance}"
    )


@pytest.mark.skip(reason="NDEV-3838")
def test_failed_trx_with_outer_deposit(
    neon_user, neon_api_client, evm_loader, operator_keypair, treasury_pool, revert_contract_caller, holder_acc
):

    # trx_status: failed
    # user_balance: outer deposit non zero
    # tree_acc: two scheduled trx in tree acc
    trx_count = 1
    iter_per_trx = 2

    evm_loader.create_balance_account(neon_user.checksum_address, neon_user.solana_account, evm_loader.sol_chain_id)

    operator_balance_initial_inner = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_initial_outer = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_initial_outer = evm_loader.get_solana_balance(treasury_pool.account)

    nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
    call_data = decode_function_signature("doTrivialRevertAferIterativeActions();")
    tx0 = ScheduledTransaction(
        neon_user.neon_address,
        None,
        nonce,
        index=0,
        target=revert_contract_caller.eth_address,
        value=0,
        call_data=call_data,
        chain_id=evm_loader.sol_chain_id,
    )

    tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
    tree_acc_data.add_trx(tx0, 0xFFFF, 0)

    tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    neon_user_balance_after_tree_created_outer = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    neon_user_balance_diff = neon_user_balance_initial_outer - neon_user_balance_after_tree_created_outer
    estimated_trx_cost = tx0.gas_limit * tx0.max_fee_per_gas
    neon_user_additional_payments = PAYMENT_FOR_TREE_ACCOUNT_DELETING + PAYMENT_FOR_TRX_FINISHING * trx_count
    expected_neon_user_balance_diff = (
        estimated_trx_cost / LAMPORT_TO_INNER_SOL
        + neon_user_additional_payments
        + TRX_EXECUTION_PRICE
        + TREE_ACCOUNT_BALANCE_STRUCT_ENLARGEMENT_COST
    )

    assert (
        neon_user_balance_diff == expected_neon_user_balance_diff
    ), f"Balance has been changed more than expected. Delta {expected_neon_user_balance_diff - neon_user_balance_diff}"

    treasury_pool_balance_after_tree_created_outer = evm_loader.get_solana_balance(treasury_pool.account)
    delta_treasury_balance = treasury_pool_balance_initial_outer - treasury_pool_balance_after_tree_created_outer

    tree_acc_balance_initial_outer = evm_loader.get_solana_balance(tree_acc)
    assert (
        tree_acc_balance_initial_outer == delta_treasury_balance + neon_user_additional_payments
    ), f"Tree acc balance failed, actual {tree_acc_balance_initial_outer}"

    tree_acc_balance_initial_inner = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance
    assert (
        tree_acc_balance_initial_inner == estimated_trx_cost
    ), f"Tree acc inner balance failed, actual {tree_acc_balance_initial_inner}"

    additional_accounts = [
        revert_contract_caller.solana_address,
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]

    resp = evm_loader.execute_scheduled_trx_from_instruction(
        tx0, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
    )
    gas_used_exec = get_total_gas_used(resp)
    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)
    operator_balance_trx_finished_inner = evm_loader.get_operator_neon_balance(
        operator_keypair, evm_loader.sol_chain_id
    )

    exec_trx_cost = gas_used_exec * tx0.max_fee_per_gas

    expected_operator_balance_trx_finished_inner = operator_balance_initial_inner + exec_trx_cost
    assert (
        operator_balance_trx_finished_inner == expected_operator_balance_trx_finished_inner
    ), f"Operator balance failed. Diff {operator_balance_trx_finished_inner - expected_operator_balance_trx_finished_inner}"

    evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_acc)

    treasury_pool_balance_tree_destroyed = evm_loader.get_solana_balance(treasury_pool.account)
    neon_user_inner_balance_tree_destroyed = evm_loader.get_neon_balance(
        neon_user.neon_address, evm_loader.sol_chain_id
    )

    expected_neon_user_balance_remainder = int(tx0.gas_limit - gas_used_exec) * tx0.max_fee_per_gas
    assert neon_user_inner_balance_tree_destroyed == expected_neon_user_balance_remainder, (
        f"Expected {expected_neon_user_balance_remainder}, but got {neon_user_inner_balance_tree_destroyed},"
        f"Delta {(neon_user_inner_balance_tree_destroyed - expected_neon_user_balance_remainder) / LAMPORT_TO_INNER_SOL}"
    )

    expected_treasury_pool_balance = (
        treasury_pool_balance_initial_outer + OPERATOR_FEE_TO_NEON * iter_per_trx * trx_count
    )
    assert treasury_pool_balance_tree_destroyed == expected_treasury_pool_balance, (
        f"Treasury pool balance is failed. "
        f"DELTA {treasury_pool_balance_initial_outer - expected_treasury_pool_balance}"
    )


@pytest.mark.skip(reason="NDEV-3838")
def test_skipped_trx_with_outer_deposit(
    neon_user, evm_loader, operator_keypair, treasury_pool, basic_contract, neon_api_client, holder_acc
):
    # trx_status: skipped
    # user_balance: only outer deposit
    # tree_acc: two schd trx in tree acc

    trx_count = 2
    count_of_skipped_trx = 1
    iter_per_trx = 2

    evm_loader.create_balance_account(neon_user.checksum_address, neon_user.solana_account, evm_loader.sol_chain_id)
    operator_balance_initial_inner = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_initial_outer = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_initial_outer = evm_loader.get_solana_balance(treasury_pool.account)

    nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
    call_data = decode_function_signature("setNumber(uint256)", args=[10])

    tx_0 = ScheduledTransaction(
        neon_user.neon_address,
        None,
        nonce,
        0,
        target=basic_contract.eth_address,
        value=0,
        call_data=b"",
        chain_id=evm_loader.sol_chain_id,
    )

    tx_1 = ScheduledTransaction(
        neon_user.neon_address,
        None,
        nonce,
        1,
        target=basic_contract.eth_address,
        value=0,
        call_data=call_data,
        chain_id=evm_loader.sol_chain_id,
    )

    tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
    tree_acc_data.add_trx(tx_0, 1, 0)
    tree_acc_data.add_trx(tx_1, 0xFFFF, 1)
    tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    neon_user_balance_after_tree_created_outer = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    neon_user_balance_diff = neon_user_balance_initial_outer - neon_user_balance_after_tree_created_outer
    estimated_trx_cost = (tx_0.gas_limit * tx_0.max_fee_per_gas) + (tx_1.gas_limit * tx_1.max_fee_per_gas)
    neon_user_additional_payments = PAYMENT_FOR_TREE_ACCOUNT_DELETING + PAYMENT_FOR_TRX_FINISHING * trx_count
    expected_neon_user_balance_diff = (
        estimated_trx_cost / LAMPORT_TO_INNER_SOL
        + neon_user_additional_payments
        + TRX_EXECUTION_PRICE
        + TREE_ACCOUNT_BALANCE_STRUCT_ENLARGEMENT_COST
    )

    assert (
        neon_user_balance_diff == expected_neon_user_balance_diff
    ), f"Balance has been changed more than expected. Delta {expected_neon_user_balance_diff - neon_user_balance_diff}"

    treasury_pool_balance_after_tree_created_outer = evm_loader.get_solana_balance(treasury_pool.account)
    delta_treasury_balance = treasury_pool_balance_initial_outer - treasury_pool_balance_after_tree_created_outer

    tree_acc_balance_initial_outer = evm_loader.get_solana_balance(tree_acc)
    assert (
        tree_acc_balance_initial_outer == delta_treasury_balance + neon_user_additional_payments
    ), f"Tree acc balance failed, actual {tree_acc_balance_initial_outer}"

    tree_acc_balance_initial_inner = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance
    assert (
        tree_acc_balance_initial_inner == estimated_trx_cost
    ), f"Tree acc inner balance failed, actual {tree_acc_balance_initial_inner}"

    additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(evm_loader.sol_chain_id)]

    resp = evm_loader.execute_scheduled_trx_from_instruction(
        tx_0, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
    )
    gas_used_exec = get_total_gas_used(resp)
    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)

    operator_balance_trx_finished_inner = evm_loader.get_operator_neon_balance(
        operator_keypair, evm_loader.sol_chain_id
    )

    exec_trx_cost = gas_used_exec * tx_0.max_fee_per_gas
    expected_operator_balance_inner = operator_balance_initial_inner + exec_trx_cost
    assert (
        operator_balance_trx_finished_inner == expected_operator_balance_inner
    ), f"Operator balance failed. Diff {operator_balance_trx_finished_inner - expected_operator_balance_inner}"

    resp = evm_loader.skip_scheduled_trx_from_instruction(tx_1, operator_keypair, tree_acc, holder_acc)
    gas_used_skipped = get_total_gas_used(resp)
    tree_acc_balance_after_skip_outer = evm_loader.get_solana_balance(tree_acc)

    # payment for trx finishing for skipped trx haven't been charged
    expected_tree_acc_balance_after_skip_outer = tree_acc_balance_initial_outer - PAYMENT_FOR_TRX_FINISHING * (
        trx_count - count_of_skipped_trx
    )
    assert (
        tree_acc_balance_after_skip_outer == expected_tree_acc_balance_after_skip_outer
    ), f"Tree acc balance after trx skipping failed, Delta {expected_tree_acc_balance_after_skip_outer-tree_acc_balance_after_skip_outer}"
    operator_balance_trx_after_skip = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    skip_trx_cost = gas_used_skipped * tx_1.max_fee_per_gas

    expected_operator_balance_after_skip = operator_balance_trx_finished_inner + skip_trx_cost
    assert (
        operator_balance_trx_after_skip == expected_operator_balance_after_skip
    ), f"Operator balance after skip failed, Delta {expected_operator_balance_after_skip - operator_balance_trx_after_skip}"

    evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_acc)
    neon_user_balance_inner_after_tree = evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id)

    total_gas_used = gas_used_exec + gas_used_skipped
    expected_neon_user_balance_remainder = estimated_trx_cost - total_gas_used * tx_0.max_fee_per_gas
    assert neon_user_balance_inner_after_tree == expected_neon_user_balance_remainder, (
        f"Expected {expected_neon_user_balance_remainder}, but got {neon_user_balance_inner_after_tree},"
        f"Delta {(neon_user_balance_inner_after_tree - expected_neon_user_balance_remainder)}"
    )

    treasury_pool_balance_tree_destroyed_outer = evm_loader.get_solana_balance(treasury_pool.account)
    expected_treasury_pool_balance = (
        treasury_pool_balance_initial_outer
        + OPERATOR_FEE_TO_NEON * iter_per_trx * (trx_count - count_of_skipped_trx)
        + PAYMENT_FOR_TRX_FINISHING * count_of_skipped_trx
    )
    assert treasury_pool_balance_tree_destroyed_outer == expected_treasury_pool_balance, (
        f"Treasury pool balance is failed. "
        f"DELTA {treasury_pool_balance_initial_outer - expected_treasury_pool_balance}"
    )
