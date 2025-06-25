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


def test_successful_trx_balance_with_outer_deposit(
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

    # #TODO Dont like hardcoded values - Fix it
    assert delta_treasury_balance == 2_916_240, f"Deposit amount failed, actual {delta_treasury_balance}"

    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    assert (
        tree_acc_balance == delta_treasury_balance + deposit_to_tree_acc
    ), f"Tree acc balance failed, actual {tree_acc_balance}"

    print(f"Neon_user {neon_user_balance_after_tree}")
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

    evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_acc)
    print("\n----Balances after tree_acc is destroyed----")

    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_operator_neon_balance(operator_keypair, evm_loader.sol_chain_id)
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    assert tree_acc_balance == 0, "Tree_acc balance's supposed to be 0"

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")


def test_failed_trx_balance_with_inner_deposit(
    neon_user, neon_api_client, evm_loader, operator_keypair, treasury_pool, basic_contract, solana_account
):

    # trx_status: success
    # user_balance: inner deposit non zero
    # tree_acc: two scheduled trx in tree acc

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

    evm_loader.create_balance_account(neon_user.checksum_address, neon_user.solana_account, evm_loader.sol_chain_id)
    holder_acc = evm_loader.create_holder(operator_keypair)

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
        max_fee_per_gas=3_000_000_000,
        max_priority_fee_per_gas=2_500_000_000,
        gas_limit=30_000_000,
        target=None,
        chain_id=evm_loader.sol_chain_id,
    )
    tx1 = ScheduledTransaction(
        neon_user.neon_address,
        None,
        nonce,
        index=1,
        target=caller_contract.eth_address,
        max_fee_per_gas=3_000_000_000,
        max_priority_fee_per_gas=2_500_000_000,
        gas_limit=30_000_000,
        call_data=data_call,
        chain_id=evm_loader.sol_chain_id,
    )

    tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
    tree_acc_data.add_trx(tx0, 1, 0)
    tree_acc_data.add_trx(tx1, 0xFFFF, 1)

    tree_account = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    print("\n----Balances after tree acc was created----")

    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_account)

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")

    additional_accounts_call = [
        caller_contract.solana_address,
        basic_contract.solana_address,
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]
    evm_loader.write_transaction_to_holder_account(tx0.encode(), holder_acc, operator_keypair)
    evm_loader.execute_scheduled_trx_from_instruction(
        tx0, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts_deploy
    )

    evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)

    evm_loader.execute_scheduled_trx_from_instruction(
        tx1, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts_call
    )
    evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)

    evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_account)

    # recipient = NeonUser(evm_loader.loader_id)
    #
    # # Balance
    # holder_acc_balance = evm_loader.get_solana_balance(holder_acc)
    # operator_balance = evm_loader.get_solana_balance(operator_keypair.pubkey())
    # neon_user_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    # treasury_pool_balance = evm_loader.get_solana_balance(treasury_pool.account)
    #
    # print(f"{neon_user_balance_before=}")
    # print(f"{operator_balance=}")
    # print(f"{treasury_pool_balance=}")
    # print(f"{holder_acc_balance=}")
    #
    # nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
    # call_data = decode_function_signature("setNumber(uint256)", args=[10])
    # trx_estimate_obj_list = []
    # for i in range(3):
    #     trx_estimate_obj_list.append(
    #         ScheduledTrxEstimateRequest(
    #             neon_user.checksum_address, basic_contract.address, data, child_transaction=hex(3)
    #         )
    #     )
    # trx_estimate_obj_list.append(
    #     ScheduledTrxEstimateRequest(
    #         neon_user.checksum_address, basic_contract.address, data, child_transaction="0xFFFF"
    #     )
    # )
    #
    # tx_0 = ScheduledTransaction(
    #     neon_user.neon_address,
    #     None,
    #     nonce,
    #     0,
    #     target=basic_contract.eth_address,
    #     value=0,
    #     call_data=call_data,
    #     chain_id=evm_loader.sol_chain_id,
    # )
    #
    # tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
    # tree_acc_data.add_trx(tx_0, 0xFFFF, 0)
    # tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)
    #
    #
    # trx_estimate_obj_list: list[ScheduledTrxEstimateRequest] = []
    # for i in range(trx_count):
    #     trx_estimate_obj_list.append(
    #         ScheduledTrxEstimateRequest(
    #             neon_user.checksum_address, erc20_spl_mintable.address, call_data[i], child_transaction="0xFFFF"
    #         )
    #     )
    # estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
    #
    # trxs = []
    # for i in range(trx_count):
    #     trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))
    #
    # tree_acc_data = CreateTreeAccMultipleData(
    #     nonce=estimate_result["nonce"],
    #     max_fee_per_gas=estimate_result["maxFeePerGas"],
    #     max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
    # )
    # tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
    # tree_acc_data.add_trx(trxs[1], 0xFFFF, 0)
    #
    # tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)
    #
    # print("\n----Balances after tree acc was created----")
    #
    # # Expected neon_user_balance --> tree_acc + treasury_acc --> tree_acc (deposit)
    # holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    # operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    # neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    # treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    # tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    #
    # print(f"Delta neon_user {neon_user_balance_after_tree}")
    # print(f"Delta operator {operator_balance_after_tree}")
    # print(f"Delta holder {holder_acc_balance_after_tree}")
    # print(f"Delta treasury {treasury_pool_balance_after_tree}")
    # print(f"Tree Acc balance {tree_acc_balance}")
    #
    # additional_accounts = [
    #     Pubkey.from_string(evm_loader.ether2program(erc20_spl_mintable.address)[0]),  # solana_address
    #     neon_user.get_balance_account(evm_loader.sol_chain_id),
    # ]
    #
    # for trx in trxs:
    #     evm_loader.execute_scheduled_trx_from_instruction_with_details(
    #         trx, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
    #     )
    #     evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)
    #
    # print("\n----Balances after trx is finished----")
    #
    # holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    # operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    # neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    # treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    # tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    #
    # print(f"Delta neon_user {neon_user_balance_after_tree}")
    # print(f"Delta operator {operator_balance_after_tree}")
    # print(f"Delta holder {holder_acc_balance_after_tree}")
    # print(f"Delta treasury {treasury_pool_balance_after_tree}")
    # print(f"Tree Acc balance {tree_acc_balance}")
    #
    # evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_acc)
    #
    # print("\n----Balances after tree_acc is destroyed----")
    #
    # holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    # operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    # neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    # treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    # tree_acc_balance = evm_loader.get_solana_balance(tree_acc)
    #
    # assert tree_acc_balance == 0, "Tree_acc balance's supposed to be 0"
    #
    # print(f"Delta neon_user {neon_user_balance_after_tree}")
    # print(f"Delta operator {operator_balance_after_tree}")
    # print(f"Delta holder {holder_acc_balance_after_tree}")
    # print(f"Delta treasury {treasury_pool_balance_after_tree}")
    # print(f"Tree Acc balance {tree_acc_balance}")
