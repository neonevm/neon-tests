from solders.pubkey import Pubkey

from utils.helpers import decode_function_signature
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData
from utils.scheduled_trx import ScheduledTrxEstimateRequest


def test_iter_successful_trx_balance_with_outer_deposit(
    neon_user, evm_loader, operator_keypair, web3_client_sol, treasury_pool, common_contract, solana_account
):
    # trx: non-iterable (1 solana trx in chain)
    # trx_status: successful
    # user_balance: only outer deposit
    # tree_acc: one schd trx in tree acc

    holder_acc = evm_loader.create_holder(operator_keypair)

    # Balance
    holder_acc_balance = evm_loader.get_solana_balance(holder_acc)
    operator_balance = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
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
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")

    evm_loader.write_transaction_to_holder_account(tx0.encode(), holder_acc, operator_keypair)
    additional_accounts = [
        Pubkey.from_string(evm_loader.ether2program(common_contract.address)[0]),  # solana_address
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]

    evm_loader.execute_scheduled_trx_from_instruction_with_details(
        tx0, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
    )

    evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)
    print("\n----Balances after trx is finished----")

    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
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
    operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    assert tree_acc_balance == 0, "Tree_acc balance's supposed to be 0"

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")


def test_non_iter_failed_trx_balance_with_outer_deposit(
    neon_user, evm_loader, operator_keypair, web3_client_sol, treasury_pool, erc20_spl_mintable, solana_account
):

    # trx: non-iterable (1 solana trx in chain)
    # trx_status: failed
    # user_balance: only outer deposit
    # tree_acc: two schd trx in tree acc

    holder_acc = evm_loader.create_holder(operator_keypair)
    recipient = NeonUser(evm_loader.loader_id)

    # Balance
    holder_acc_balance = evm_loader.get_solana_balance(holder_acc)
    operator_balance = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_before = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance = evm_loader.get_solana_balance(treasury_pool.account)

    print(f"{neon_user_balance_before=}")
    print(f"{operator_balance=}")
    print(f"{treasury_pool_balance=}")
    print(f"{holder_acc_balance=}")

    amount_to_transfer = 1_000

    erc20_spl_mintable.pop_up_balance(
        evm_loader, recipient=neon_user, pda_amount=amount_to_transfer, ata_amount=amount_to_transfer
    )

    transfer_amount = 200
    approve_amount = 1000
    trx_count = 2

    data_0 = decode_function_signature("approve(address,uint256)", [neon_user.checksum_address, approve_amount])
    data_1 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, transfer_amount])

    call_data: list = [data_0, data_1]

    trx_estimate_obj_list: list[ScheduledTrxEstimateRequest] = []
    for i in range(trx_count):
        trx_estimate_obj_list.append(
            ScheduledTrxEstimateRequest(
                neon_user.checksum_address, erc20_spl_mintable.address, call_data[i], child_transaction="0xFFFF"
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
    tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
    tree_acc_data.add_trx(trxs[1], 0xFFFF, 0)

    tree_acc = evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

    print("\n----Balances after tree acc was created----")

    # Expected neon_user_balance --> tree_acc + treasury_acc --> tree_acc (deposit)
    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")

    additional_accounts = [
        Pubkey.from_string(evm_loader.ether2program(erc20_spl_mintable.address)[0]),  # solana_address
        neon_user.get_balance_account(evm_loader.sol_chain_id),
    ]

    for trx in trxs:
        evm_loader.execute_scheduled_trx_from_instruction_with_details(
            trx, operator_keypair, holder_acc, tree_acc, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_acc, holder_acc)

    print("\n----Balances after trx is finished----")

    holder_acc_balance_after_tree = evm_loader.get_solana_balance(holder_acc)
    operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
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
    operator_balance_after_tree = evm_loader.get_solana_balance(operator_keypair.pubkey())
    neon_user_balance_after_tree = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
    treasury_pool_balance_after_tree = evm_loader.get_solana_balance(treasury_pool.account)
    tree_acc_balance = evm_loader.get_solana_balance(tree_acc)

    assert tree_acc_balance == 0, "Tree_acc balance's supposed to be 0"

    print(f"Delta neon_user {neon_user_balance_after_tree}")
    print(f"Delta operator {operator_balance_after_tree}")
    print(f"Delta holder {holder_acc_balance_after_tree}")
    print(f"Delta treasury {treasury_pool_balance_after_tree}")
    print(f"Tree Acc balance {tree_acc_balance}")
