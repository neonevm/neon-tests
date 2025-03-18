from eth_utils import abi

from utils.consts import wSOL
from utils.helpers import decode_function_signature, wait_condition
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest


class TestRPCNeonGetPendingTransactions:

    def test_neon_get_pending_scheduled_transaction_done(
        self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        nonce = hex(web3_client_sol.get_nonce(neon_user.checksum_address))
        data = decode_function_signature("setNumber(uint256)", [18])

        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_account = evm_loader.create_tree_account(
            neon_user, treasury_pool, tx.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )

        expected_status = "Done"
        wait_condition(
            lambda: web3_client_sol.get_pending_transactions(neon_user.checksum_address)[nonce][0]["status"]
            == expected_status,
            delay=2,
            timeout_sec=60,
        )
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

    def test_neon_get_pending_scheduled_transaction_no_tx_body(
        self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        nonce = hex(web3_client_sol.get_nonce(neon_user.checksum_address))
        data = decode_function_signature("setNumber(uint256)", [18])

        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
        )
        tree_acc_data.add_trx(tx, 0xFFFF, 0)
        tree_account = evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        expected_status = "NoTransactionBody"
        wait_condition(
            lambda: web3_client_sol.get_pending_transactions(neon_user.checksum_address)[nonce][0]["status"]
            == expected_status,
            timeout_sec=60,
            delay=2,
            log=10,
        )
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=1)

    def test_multiple_scheduled_trx_with_failed_trx_skipped_and_wait_for_parent_tx(
        self,
        web3_client_sol,
        neon_user,
        treasury_pool,
        revert_contract_caller,
        event_caller_contract,
        evm_loader,
        counter_contract,
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()

        gas_limit = 30000000
        call_data_trx0 = abi.function_signature_to_4byte_selector("doAssert()")
        call_data_trx1 = abi.function_signature_to_4byte_selector("indexedArgs()")

        call_data_counter = decode_function_signature("moreInstructionWithLogs(uint256,uint256)", [0, 1000])

        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            target=revert_contract_caller.address,
            call_data=call_data_trx0,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            chain_id=web3_client_sol.chain_id,
        )

        tx1 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=1,
            target=revert_contract_caller.address,
            call_data=call_data_trx1,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            chain_id=web3_client_sol.chain_id,
        )
        tx2 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=2,
            target=counter_contract.address,
            call_data=call_data_counter,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            chain_id=web3_client_sol.chain_id,
        )
        tx3 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=3,
            target=counter_contract.address,
            call_data=call_data_counter,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            chain_id=web3_client_sol.chain_id,
        )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx0, 1, 0)
        tree_acc_data.add_trx(tx1, 0xFFFF, 1)
        tree_acc_data.add_trx(tx2, 3, 0)
        tree_acc_data.add_trx(tx3, 0xFFFF, 1)

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )

        web3_client_sol.send_all_scheduled_transactions([tx0, tx1])  # dont send tx2

        resp1 = web3_client_sol.wait_for_transaction_receipt(tx0.hash())
        assert resp1["status"] == 0
        resp2 = web3_client_sol.wait_for_transaction_receipt(tx1.hash())
        assert resp2["status"] == 0

        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) >= 1
        assert pending_trx[hex(nonce)][0]["status"] == "Done"
        assert pending_trx[hex(nonce)][1]["status"] == "Skipped"
        assert pending_trx[hex(nonce)][2]["status"] == "NoTransactionBody"
        assert pending_trx[hex(nonce)][3]["status"] == "WaitForParentTransactions"
        assert pending_trx[hex(nonce)][0]["hash"][2:] == tx0.hash().hex()
