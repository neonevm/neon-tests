import random

import allure
import eth_abi
import pytest
from eth_utils import abi

from utils.consts import wSOL, LAMPORT_PER_SOL
from utils.helpers import wait_condition
from utils.models.result import EthGetBlockByHashResult
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest
from utils.web3client import BASE_MAX_PRIORITY_FEE


@allure.feature("Solana native")
@allure.story("Test sending scheduled transaction")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestScheduledTrx:
    def test_send_simple_single_trx(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)
        wait_condition(lambda: hex(tx.nonce) in web3_client_sol.get_pending_transactions(neon_user.checksum_address))
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert pending_trx[hex(tx.nonce)][0]["status"] in ("Done", "InProgress")
        assert common_contract.functions.getNumber().call() == contract_data

    def test_multiple_scheduled_trx(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )

        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
        gas_limit = 30000000

        trxs = []
        for i in range(4):
            trxs.append(
                ScheduledTransaction(
                    neon_user.neon_address,
                    None,
                    nonce,
                    index=i,
                    target=common_contract.address,
                    call_data=data,
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                    gas_limit=gas_limit,
                    chain_id=web3_client_sol.chain_id,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        tree_acc_data.add_trx(trxs[0], 3, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 3, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)

        evm_loader.create_tree_account_multiple(
            neon_user,
            treasury_pool,
            tree_acc_data.data,
            wSOL["address_spl"],
            chain_id=web3_client_sol.chain_id,
            payer_nonce=nonce,
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            resp = web3_client_sol.wait_for_transaction_receipt(trx.hash(), timeout=180)
            assert resp["status"] == 1, f"Trx {trx.hash().hex()} failed: receipt - {resp}"
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) >= 1
        assert pending_trx[hex(nonce)][0]["status"] == "Done"
        assert pending_trx[hex(nonce)][0]["hash"][2:] == trxs[0].hash().hex()

    def test_multiple_scheduled_trx_with_failed_trx(
        self, web3_client_sol, neon_user, treasury_pool, revert_contract_caller, event_caller_contract, evm_loader
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
        gas_limit = 30000000

        call_data_trx0 = abi.function_signature_to_4byte_selector("doAssert()")
        call_data_trx1 = abi.function_signature_to_4byte_selector("indexedArgs()")

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
        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx0, 1, 0)
        tree_acc_data.add_trx(tx1, 0xFFFF, 1)
        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )

        web3_client_sol.send_all_scheduled_transactions([tx0, tx1])
        resp1 = web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)
        assert resp1["status"] == 0
        resp2 = web3_client_sol.wait_for_transaction_receipt(tx1.hash(), timeout=180)
        assert resp2["status"] == 0
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) >= 1
        assert pending_trx[hex(nonce)][0]["status"] == "Done"
        assert pending_trx[hex(nonce)][0]["hash"][2:] == tx0.hash().hex()

    def test_create_2_tree_accounts_with_the_same_nonce(
        self, web3_client_sol, evm_loader, neon_user, treasury_pool, common_contract
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(["uint256"], [1])

        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, call_data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx0 = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_acc = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc.add_trx(tx0, 0xFFFF, 0)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc.data, wSOL["address_spl"], payer_nonce=nonce
        )
        with pytest.raises(AssertionError, match="transaction with the same nonce already exists"):
            evm_loader.create_tree_account_multiple(
                neon_user, treasury_pool, tree_acc.data, wSOL["address_spl"], payer_nonce=nonce
            )
        web3_client_sol.send_scheduled_transaction(tx0)
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=1)

    @pytest.mark.skip("NDEV-3453")
    def test_scheduled_trx_send_tokens_to_neon_chain_contract(
        self, neon_user, evm_loader, event_caller_contract, web3_client_sol, treasury_pool
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("indexedArgs()")
        value = 100000

        trx_estimate_obj = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, event_caller_contract.address, call_data, value=value
        )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx0 = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])
        web3_client_sol.send_scheduled_transaction(tx0)
        receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)
        event_logs = event_caller_contract.events.IndexedArgs().process_receipt(receipt)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 2
        assert event_logs[0].args.who == neon_user.checksum_address
        assert event_logs[0].args.value == value
        assert event_logs[0].event == "IndexedArgs"

    def test_scheduled_trx_send_tokens_to_sol_chain_contract(
        self, neon_user, evm_loader, event_caller_sol_chain, web3_client_sol, treasury_pool, solana_account
    ):
        evm_loader.deposit_wrapped_sol_from_solana_to_neon(
            neon_user.solana_account,
            "0x" + neon_user.neon_address.hex(),
            int(1 * LAMPORT_PER_SOL),
        )
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("indexedArgs()")
        value = 100000

        trx_estimate_obj = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, event_caller_sol_chain.address, call_data, value=value
        )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx0 = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_scheduled_transaction(tx0)
        receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)
        event_logs = event_caller_sol_chain.events.IndexedArgs().process_receipt(receipt)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 2
        assert event_logs[0].args.who == neon_user.checksum_address
        assert event_logs[0].args.value == value
        assert event_logs[0].event == "IndexedArgs"

    def test_scheduled_trx_with_timestamp(
        self, block_timestamp_contract, web3_client_sol, neon_user, treasury_pool, evm_loader, json_rpc_client
    ):
        contract, _ = block_timestamp_contract
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        trx_count = 6
        call_data = []
        for i in range(trx_count):
            v1 = random.randint(1, 100)
            v2 = random.randint(1, 100)
            call_data.append(
                abi.function_signature_to_4byte_selector("addDataToMapping(uint256,uint256)")
                + eth_abi.encode(["uint256", "uint256"], [v1, v2])
            )
        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
        gas_limit = 30000000

        trxs = []
        for i in range(trx_count):
            trxs.append(
                ScheduledTransaction(
                    neon_user.neon_address,
                    None,
                    nonce,
                    index=i,
                    target=contract.address,
                    call_data=call_data[i],
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                    gas_limit=gas_limit,
                    chain_id=web3_client_sol.chain_id,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )
        tree_acc_data.add_trx(trxs[0], 1, 0)
        if trx_count > 2:
            for i in range(1, trx_count - 1):
                tree_acc_data.add_trx(trxs[i], i + 1, 1)
        tree_acc_data.add_trx(trxs[trx_count - 1], 0xFFFF, 1)
        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            receipt = web3_client_sol.wait_for_transaction_receipt(trx.hash(), timeout=180)
            assert receipt["status"] == 1, f"Trx {trx.hash().hex()} failed: receipt - {receipt}"
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        event_logs = contract.events.DataAdded().process_receipt(receipt)
        added_timestamp = event_logs[0]["args"]["timestamp"]

        assert added_timestamp <= int(tx_block_timestamp, 16)
        assert contract.functions.getDataFromMapping(added_timestamp).call() == [v1, v2]

    def test_scheduled_trx_with_small_gas_limit(
        self, block_timestamp_contract, web3_client_sol, neon_user, treasury_pool, evm_loader, event_caller_contract
    ):
        contract, _ = block_timestamp_contract

        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("addDataToMapping(uint256,uint256)") + eth_abi.encode(
            ["uint256", "uint256"], [1, 2]
        )
        gas_limit = 3000
        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()

        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            target=contract.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            chain_id=web3_client_sol.chain_id,
        )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)

        with pytest.raises(AssertionError, match="Transaction Tree - transaction requires at least 25'000 gas limit"):
            evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])

    def test_long_chain_iterative_scheduled_trx(
        self, web3_client_sol, neon_user, treasury_pool, evm_loader, json_rpc_client, counter_contract
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        total_trx_count = 8

        call_data_counter = abi.function_signature_to_4byte_selector(
            "moreInstructionWithLogs(uint256,uint256)"
        ) + eth_abi.encode(["uint256", "uint256"], [0, 1000])

        trx_estimate_obj_list = []
        for _ in range(total_trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, counter_contract.address, call_data_counter)
            )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(total_trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(trxs[0], 1, 0)
        if total_trx_count > 2:
            for i in range(1, total_trx_count - 1):
                tree_acc_data.add_trx(trxs[i], i + 1, 1)
        tree_acc_data.add_trx(trxs[total_trx_count - 1], 0xFFFF, 1)
        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            receipt = web3_client_sol.wait_for_transaction_receipt(trx.hash(), timeout=180)
            assert receipt["status"] == 1, f"Trx {trx.hash().hex()} failed: receipt - {receipt}"
