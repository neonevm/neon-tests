from solders.pubkey import Pubkey
from utils.consts import LAMPORT_PER_SOL
from utils.helpers import decode_function_signature
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData
from utils.scheduled_trx import ScheduledTrxEstimateRequest


def test_iter_successful_trx_balance_with_inner_deposit(
    neon_user, evm_loader, operator_keypair, web3_client_sol, treasury_pool, common_contract, solana_account
):
    # Inner deposit
    evm_loader.deposit_wrapped_sol_from_solana_to_neon(
        neon_user.solana_account,
        "0x" + neon_user.neon_address.hex(),
        int(1 * LAMPORT_PER_SOL),
    )

    # Create holder account
    holder_acc = evm_loader.create_holder(operator_keypair)

    # Balance
    holder_acc_balance = evm_loader.get_solana_balance(holder_acc)
    operator_balance = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_before = web3_client_sol.get_balance(neon_user.checksum_address)
    treasury_pool_balance = evm_loader.get_solana_balance(treasury_pool.account)

    print(f"{neon_user_balance_before=}")
    print(f"{operator_balance=}")
    print(f"{treasury_pool_balance=}")
    print(f"{holder_acc_balance=}")

    nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
    call_data = decode_function_signature("setNumber(uint256)", args=[10])

    trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, call_data)
    estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

    tx0 = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

    tree_acc_data = CreateTreeAccMultipleData(
        nonce=nonce,
        max_fee_per_gas=estimate_result["maxFeePerGas"],
        max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
    )
    tree_acc_data.add_trx(tx0, 0xFFFF, 0)
    tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    print("\n----Balances after tree acc was created----")

    # Expected neon_user_balance --> tree_acc + treasury_acc --> tree_acc (deposit)
    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_after_tree = web3_client_sol.get_balance(neon_user.checksum_address)
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")

    additional_accounts = [
        Pubkey.from_string(evm_loader.ether2program(common_contract.address)[0]),  # solana_address
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]

    evm_loader.execute_scheduled_trx_from_instruction_with_details(
        tx0, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
    )

    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)
    print("\n----Balances after trx is finished----")

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")


def test_non_iter_failed_trx_balance_with_outer_deposit(
    neon_user, evm_loader, operator_keypair, web3_client_sol, treasury_pool, common_contract, solana_account
):

    # Create holder account
    holder_acc = evm_loader.create_holder(operator_keypair)

    # Balance
    holder_acc_balance = evm_loader.get_solana_balance(holder_acc)
    operator_balance = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_before = web3_client_sol.get_balance(neon_user.checksum_address)
    treasury_pool_balance = evm_loader.get_solana_balance(treasury_pool.account)

    print(f"{neon_user_balance_before=}")
    print(f"{operator_balance=}")
    print(f"{treasury_pool_balance=}")
    print(f"{holder_acc_balance=}")

    nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
    call_data = decode_function_signature("setNumber(uint256)", args=[10])

    trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, call_data)
    estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

    tx0 = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

    tree_acc_data = CreateTreeAccMultipleData(
        nonce=nonce,
        max_fee_per_gas=estimate_result["maxFeePerGas"],
        max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
    )
    tree_acc_data.add_trx(tx0, 0xFFFF, 0)
    tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    print("\n----Balances after tree acc was created----")

    # Expected neon_user_balance --> tree_acc + treasury_acc --> tree_acc (deposit)
    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_after_tree = web3_client_sol.get_balance(neon_user.checksum_address)
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")

    additional_accounts = [
        Pubkey.from_string(evm_loader.ether2program(common_contract.address)[0]),  # solana_address
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]

    evm_loader.execute_scheduled_trx_from_instruction_with_details(
        tx0, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
    )

    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)
    print("\n----Balances after trx is finished----")

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")
    # web3_client_sol.send_scheduled_transaction(tx0)
    # check_trx_is_success(web3_client_sol, evm_loader, tx0.hash().hex())
    # receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)
    # event_logs = event_caller_sol_chain.events.IndexedArgs().process_receipt(receipt)
    # assert len(event_logs) == 1
    # assert len(event_logs[0].args) == 2
    # assert event_logs[0].args.who == neon_user.checksum_address
    # assert event_logs[0].args.value == value
    # assert event_logs[0].event == "IndexedArgs"
    #
    #
    # balance_after = web3_client_sol.get_balance(neon_user.checksum_address)
    # print(balance_after)

    #
    # withdraw_neon_to_solana_sol_sign(
    #     neon_user, solana_account, withdraw_contract_sol_chain, evm_loader, web3_client_sol, treasury_pool
    # )
