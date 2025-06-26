import logging

import eth_abi
from eth_utils import abi

from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.contract import get_contract_bin
from integration.tests.neon_evm.utils.ethereum import create_contract_address
from utils.consts import LAMPORT_PER_SOL
from utils.helpers import decode_function_signature
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData

from utils.types import Contract


LAMPORT_TO_INNER_SOL = 10**9
LOG = logging.getLogger(__name__)


def test_successful_single_trx_with_outer_deposit(
    neon_user, evm_loader, operator_keypair, treasury_pool, basic_contract, neon_api_client
):
    # trx_status: successful
    # user_balance: only outer deposit
    # tree_acc: one schd trx in tree acc

    neon_inner_balance_request = neon_api_client.get_balance(neon_user.checksum_address, evm_loader.sol_chain_id)
    neon_user_balance_sol = int(neon_inner_balance_request["value"][0]["balance"], 16)
    assert neon_user_balance_sol == 0, f"Inner sol balance is {neon_user_balance_sol}, but has to be zero"

    evm_loader.create_balance_account(neon_user.checksum_address, neon_user.solana_account, evm_loader.sol_chain_id)
    holder_acc = evm_loader.create_holder(operator_keypair)

    # Balance
    holder_acc_balance = evm_loader.get_solana_balance(holder_acc)
    operator_balance = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance = evm_loader.get_solana_balance(treasury_pool.account)

    print(f"{neon_user_balance_before=}")
    print(f"{neon_user_balance_sol=}")
    print(f"{operator_balance=}")
    print(f"{treasury_pool_balance=}")
    print(f"{holder_acc_balance=}")

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

    print("\n----Balances after tree acc was created----")

    # Expected neon_user_balance --> tree_acc + treasury_acc --> tree_acc (deposit)
    operator_balance_after_tree = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    assert operator_balance == operator_balance_after_tree, "Operator balance has changed, but is not supposed to"

    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    delta_neon_user = neon_user_balance_before - neon_user_balance_after_tree
    estimated_gas_fee = tx_0.DEFAULTS["gas_limit"] * tx_0.DEFAULTS["max_fee_per_gas"] / LAMPORT_TO_INNER_SOL
    deposit_to_tree_acc = 10_000  # Where it comes from?
    trx_execution_price = 5_000
    # Need to ensure about deposit diff before and after
    # 1. 9_000_000 - default gas_limit * max_fee_per_gas / (10 ^ 9)
    # 2. 10_000 - deposit to tree_account
    # 3. Create_tree_acc trx - 5_000 - trx execution fee

    assert (
        delta_neon_user == estimated_gas_fee + deposit_to_tree_acc + trx_execution_price
    ), f"Balance has been changed more than expected. Delta {delta_neon_user}"

    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    delta_treasury_balance = treasury_pool_balance - treasury_pool_balance_after_tree

    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    assert (
        tree_acc_balance == delta_treasury_balance + deposit_to_tree_acc
    ), f"Tree acc balance failed, actual {tree_acc_balance}"

    tree_acc_balance_inner = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance
    assert tree_acc_balance_inner == int(
        estimated_gas_fee * LAMPORT_TO_INNER_SOL
    ), f"Tree acc inner balance failed, actual {tree_acc_balance_inner}"

    print(f"Neon_user {neon_user_balance_after_tree}")
    print(f"Tree Acc balance inner {tree_acc_balance_inner}")
    print(f"Operator {operator_balance_after_tree}")
    print(f"Treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")

    additional_accounts = [
        basic_contract.solana_address,
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]

    evm_loader.execute_scheduled_trx_from_instruction_with_details(
        tx_0, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
    )

    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)
    print("\n----Balances after trx is finished----")

    holder_acc_balance_trx_finished = evm_loader.get_solana_balance(holder_acc)
    operator_balance_trx_finished = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_trx_finished = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_trx_finished = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance_trx_finished = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_trx_finished}")
    print(f"Delta operator {operator_balance_trx_finished}")
    print(f"Delta holder {holder_acc_balance_trx_finished}")
    print(f"Delta treasury {treasury_pool_balance_trx_finished}")
    print(f"Tree Acc balance {tree_acc_balance_trx_finished}")

    assert (
        operator_balance_trx_finished > operator_balance
    ), f"Operator balance failed. It has to be greater than {operator_balance}"

    evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_acc)
    print("\n----Balances after tree_acc is destroyed----")

    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    tree_acc_balance_inner_after = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance

    assert tree_acc_balance == 0, "Tree_acc balance's supposed to be 0"
    assert (
        treasury_pool_balance == treasury_pool_balance_after_tree - deposit_to_tree_acc
    ), f"Treasury pool balance is failed. Expected {treasury_pool_balance}, but got {treasury_pool_balance_after_tree}"
    assert tree_acc_balance_inner_after == 0, "Tree acc inner balance after destroyed failed, expected to be zero"

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")


def test_success_two_trx_with_inner_deposit(
    neon_user, neon_api_client, evm_loader, operator_keypair, treasury_pool, basic_contract, solana_account
):

    # trx_status: success
    # user_balance: inner deposit non zero
    # tree_acc: two scheduled trx in tree acc

    # Assumptions
    trx_count = 2
    gas_limit = 30_000_000
    max_fee_per_gas = 3_000_000_000

    evm_loader.create_balance_account(neon_user.checksum_address, neon_user.solana_account, evm_loader.sol_chain_id)
    evm_loader.deposit_wrapped_sol_from_solana_to_neon(
        neon_user.solana_account,
        "0x" + neon_user.neon_address.hex(),
        int(1 * LAMPORT_PER_SOL),
    )

    inner_balance_request = neon_api_client.get_balance(neon_user.checksum_address, evm_loader.sol_chain_id)
    neon_user_balance_sol = int(inner_balance_request["value"][0]["balance"], 16)
    assert (
        neon_user_balance_sol == LAMPORT_PER_SOL * LAMPORT_TO_INNER_SOL
    ), f"Inner sol balance is {neon_user_balance_sol}, but has to be {LAMPORT_PER_SOL}"

    holder_acc = evm_loader.create_holder(operator_keypair)

    holder_acc_balance = evm_loader.get_solana_balance(holder_acc)
    operator_balance = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance = evm_loader.get_solana_balance(treasury_pool.account)

    print(f"{neon_user_balance_before=}")
    print(f"{neon_user_balance_sol=}")
    print(f"{operator_balance=}")
    print(f"{treasury_pool_balance=}")
    print(f"{holder_acc_balance=}")

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

    print("\n----Balances after tree acc was created----")

    # Expected neon_user_balance --> tree_acc + treasury_acc --> tree_acc (deposit)
    operator_balance_after_tree = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    assert operator_balance == operator_balance_after_tree, "Operator balance has changed, but is not supposed to"

    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    delta_neon_user = neon_user_balance_before - neon_user_balance_after_tree
    estimated_gas_fee = gas_limit * max_fee_per_gas / LAMPORT_TO_INNER_SOL
    deposit_to_tree_acc = 10_000  # Where it comes from?
    trx_execution_price = 5_000
    # Need to ensure about deposit diff before and after
    # 1. 10_000 - deposit to tree_account
    # 2. Create_tree_acc trx - 5_000 - trx execution fee

    assert (
        delta_neon_user == deposit_to_tree_acc + trx_execution_price
    ), f"Balance has been changed more than expected. Delta {delta_neon_user}"

    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    delta_treasury_balance = treasury_pool_balance - treasury_pool_balance_after_tree

    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    assert (
        tree_acc_balance == delta_treasury_balance + deposit_to_tree_acc
    ), f"Tree acc balance failed, actual {tree_acc_balance}"

    tree_acc_balance_inner = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance
    assert (
        tree_acc_balance_inner == int(estimated_gas_fee * LAMPORT_TO_INNER_SOL) * trx_count
    ), f"Tree acc inner balance failed, actual {tree_acc_balance_inner}"

    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")
    print(f"Tree Acc balance inner {tree_acc_balance_inner}")

    additional_accounts_call = [
        caller_contract.solana_address,
        basic_contract.solana_address,
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]
    evm_loader.write_transaction_to_holder_account(tx0.encode(), holder_acc, operator_keypair)
    evm_loader.execute_scheduled_trx_from_instruction_with_details(
        tx0, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts_deploy
    )

    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)

    holder_acc_balance_trx_finished = evm_loader.get_solana_balance(holder_acc)
    operator_balance_trx_finished_1 = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_trx_finished = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_trx_finished = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance_trx_finished = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_trx_finished}")
    print(f"Delta operator {operator_balance_trx_finished_1}")
    print(f"Delta holder {holder_acc_balance_trx_finished}")
    print(f"Delta treasury {treasury_pool_balance_trx_finished}")
    print(f"Tree Acc balance {tree_acc_balance_trx_finished}")

    assert (
        operator_balance_trx_finished_1 > operator_balance
    ), f"Operator balance failed. It has to be greater than {operator_balance}"

    evm_loader.execute_scheduled_trx_from_instruction(
        tx1, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts_call
    )
    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)

    operator_balance_trx_finished_2 = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)

    assert (
        operator_balance_trx_finished_2 > operator_balance_trx_finished_1
    ), f"Operator balance failed. It has to be greater than {operator_balance_trx_finished_1}"

    evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_acc)
    print("\n----Balances after tree_acc is destroyed----")

    tree_acc_balance_inner_tree_destroyed = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance

    holder_acc_balance_tree_destroyed = evm_loader.get_solana_balance(holder_acc)
    operator_balance_tree_destroyed = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_tree_destroyed = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_tree_destroyed = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance_tree_destroyed = evm_loader.get_solana_balance(tree_acc)

    assert tree_acc_balance_tree_destroyed == 0, "Tree_acc balance's supposed to be 0"
    treasury_pool_final_balance_no_fees = treasury_pool_balance_tree_destroyed - deposit_to_tree_acc * trx_count
    assert (
        treasury_pool_balance == treasury_pool_final_balance_no_fees
    ), f"Expected {treasury_pool_balance}, but got {treasury_pool_final_balance_no_fees}"
    assert (
        tree_acc_balance_inner_tree_destroyed == 0
    ), "Tree acc inner balance after destroyed failed, expected to be zero"

    print(f"Delta neon_user {neon_user_balance_tree_destroyed}")
    print(f"Delta operator {operator_balance_tree_destroyed}")
    print(f"Delta holder {holder_acc_balance_tree_destroyed}")
    print(f"Delta treasury {treasury_pool_balance_tree_destroyed}")
    print(f"Tree Acc balance {tree_acc_balance_tree_destroyed}")


def test_failed_trx_with_outer_deposit(
    neon_user, neon_api_client, evm_loader, operator_keypair, treasury_pool, basic_contract, solana_account
):

    # trx_status: failed
    # user_balance: outer deposit non zero
    # tree_acc: two scheduled trx in tree acc

    evm_loader.create_balance_account(neon_user.checksum_address, neon_user.solana_account, evm_loader.sol_chain_id)

    neon_user_balance_sol = evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id)
    assert neon_user_balance_sol == 0, f"Inner sol balance is {neon_user_balance_sol}, but has to be zero"

    holder_acc = evm_loader.create_holder(operator_keypair)

    holder_acc_balance = evm_loader.get_solana_balance(holder_acc)
    operator_balance = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance = evm_loader.get_solana_balance(treasury_pool.account)

    print(f"{neon_user_balance_before=}")
    print(f"{neon_user_balance_sol=}")
    print(f"{operator_balance=}")
    print(f"{treasury_pool_balance=}")
    print(f"{holder_acc_balance=}")

    nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
    tx0 = ScheduledTransaction(
        neon_user.neon_address,
        None,
        nonce,
        index=0,
        target=basic_contract.eth_address,
        value=0,
        call_data=b"",
        chain_id=evm_loader.sol_chain_id,
    )

    tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
    tree_acc_data.add_trx(tx0, 0xFFFF, 0)

    tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    print("\n----Balances after tree acc was created----")

    # Expected neon_user_balance --> tree_acc + treasury_acc --> tree_acc (deposit)
    operator_balance_after_tree = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    assert operator_balance == operator_balance_after_tree, "Operator balance has changed, but is not supposed to"

    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    delta_neon_user = neon_user_balance_before - neon_user_balance_after_tree
    estimated_gas_fee = tx0.DEFAULTS["gas_limit"] * tx0.DEFAULTS["max_fee_per_gas"] / LAMPORT_TO_INNER_SOL
    deposit_to_tree_acc = 10_000  # Where it comes from?
    trx_execution_price = 5_000
    # 1. 9_000_000 - default gas_limit * max_fee_per_gas / (10 ^ 9)
    # 2. 10_000 - deposit to tree_account
    # 3. Create_tree_acc trx - 5_000 - trx execution fee

    assert (
        delta_neon_user == estimated_gas_fee + deposit_to_tree_acc + trx_execution_price
    ), f"Balance has been changed more than expected. Delta {delta_neon_user}"

    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    delta_treasury_balance = treasury_pool_balance - treasury_pool_balance_after_tree

    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    assert (
        tree_acc_balance == delta_treasury_balance + deposit_to_tree_acc
    ), f"Tree acc balance failed, actual {tree_acc_balance}"

    tree_acc_balance_inner = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance
    assert tree_acc_balance_inner == int(
        estimated_gas_fee * LAMPORT_TO_INNER_SOL
    ), f"Tree acc inner balance failed, actual {tree_acc_balance_inner}"

    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")
    print(f"Tree Acc balance inner {tree_acc_balance_inner}")

    additional_accounts = [
        basic_contract.solana_address,
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]

    evm_loader.execute_scheduled_trx_from_instruction_with_details(
        tx0, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
    )

    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)

    holder_acc_balance_trx_finished = evm_loader.get_solana_balance(holder_acc)
    operator_balance_trx_finished = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_trx_finished = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_trx_finished = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance_trx_finished = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_trx_finished}")
    print(f"Delta operator {operator_balance_trx_finished}")
    print(f"Delta holder {holder_acc_balance_trx_finished}")
    print(f"Delta treasury {treasury_pool_balance_trx_finished}")
    print(f"Tree Acc balance {tree_acc_balance_trx_finished}")

    assert (
        operator_balance_trx_finished > operator_balance
    ), f"Operator balance failed. It has to be greater than {operator_balance}"

    evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_acc)
    print("\n----Balances after tree_acc is destroyed----")

    tree_acc_balance_inner_tree_destroyed = neon_api_client.get_transaction_tree(
        neon_user.neon_address.hex(), nonce, evm_loader.sol_chain_id
    ).balance

    holder_acc_balance_tree_destroyed = evm_loader.get_solana_balance(holder_acc)
    operator_balance_tree_destroyed = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_tree_destroyed = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_tree_destroyed = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance_tree_destroyed = evm_loader.get_solana_balance(tree_acc)

    assert tree_acc_balance_tree_destroyed == 0, "Tree_acc balance's supposed to be 0"
    treasury_pool_final_balance_no_fees = treasury_pool_balance_tree_destroyed - deposit_to_tree_acc
    assert (
        treasury_pool_balance == treasury_pool_final_balance_no_fees
    ), f"Expected {treasury_pool_balance}, but got {treasury_pool_final_balance_no_fees}"
    assert (
        tree_acc_balance_inner_tree_destroyed == 0
    ), "Tree acc inner balance after destroyed failed, expected to be zero"

    print(f"Delta neon_user {neon_user_balance_tree_destroyed}")
    print(f"Delta operator {operator_balance_tree_destroyed}")
    print(f"Delta holder {holder_acc_balance_tree_destroyed}")
    print(f"Delta treasury {treasury_pool_balance_tree_destroyed}")
    print(f"Tree Acc balance {tree_acc_balance_tree_destroyed}")
