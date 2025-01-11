import random

import allure
import eth_abi
import pytest
from eth_utils import abi
from solana.rpc.core import RPCException
from utils.consts import wSOL
from utils.models.result import EthGetBlockByHashResult
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData


@allure.feature("Solana native")
@allure.story("Test sending scheduled transaction")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestScheduledTrx:
    def test_send_simple_single_trx(
        self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx = ScheduledTransaction(
            neon_user.neon_address, None, nonce, 0, target=common_contract.address, call_data=data
        )
        evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode(), wSOL["address_spl"])
        web3_client_sol.wait_for_transaction_receipt(tx.hash())
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) == 1
        assert pending_trx["0x0"][0]["status"] in ("Done", "InProgress")
        assert common_contract.functions.getNumber().call() == contract_data

    def test_multiple_scheduled_trx(
        self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trxs = []
        max_fee_per_gas = 3000000000
        max_priority_fee_per_gas = 2500000000
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
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(trxs[0], 3, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 3, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])

        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            resp = web3_client_sol.wait_for_transaction_receipt(trx.hash())
            assert resp["status"] == 1
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) == 1
        assert pending_trx["0x0"][0]["status"] == "Done"
        assert pending_trx["0x0"][0]["hash"][2:] == trxs[0].hash().hex()

    def test_multiple_scheduled_trx_with_failed_trx(
        self,
        web3_client_sol,
        neon_user,
        treasury_pool,
        revert_contract_caller,
        event_caller_contract,
        evm_loader
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("doAssert()")
        gas_limit = 30000000
        max_fee_per_gas = 3000000000
        max_priority_fee_per_gas = 2500000000

        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            target=revert_contract_caller.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit
        )
        call_data = abi.function_signature_to_4byte_selector("indexedArgs()")
        tx1 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=1,
            target=revert_contract_caller.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit
        )
        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx0, 1, 0)
        tree_acc_data.add_trx(tx1, 0xFFFF, 1)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])

        web3_client_sol.send_all_scheduled_transactions([tx0, tx1])
        resp1 = web3_client_sol.wait_for_transaction_receipt(tx0.hash())
        assert resp1["status"] == 0
        resp2 = web3_client_sol.wait_for_transaction_receipt(tx1.hash())
        assert resp2["status"] == 0
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) == 1
        assert pending_trx["0x0"][0]["status"] == "Done"
        assert pending_trx["0x0"][0]["hash"][2:] == tx0.hash().hex()

    def test_create_2_tree_accounts_with_the_same_nonce(
        self, web3_client_sol, evm_loader, neon_user, treasury_pool, common_contract
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(["uint256"], [1])
        tx0 = ScheduledTransaction(
            neon_user.neon_address, None, nonce, index=0, target=common_contract.address, call_data=data
        )
        tree_acc = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc.add_trx(tx0, 0xFFFF, 0)

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc.data, wSOL["address_spl"], payer_nonce=nonce
        )
        with pytest.raises(RPCException, match="transaction with the same nonce already exists"):
            evm_loader.create_tree_account_multiple(
                neon_user, treasury_pool, tree_acc.data, wSOL["address_spl"], payer_nonce=nonce
            )

    @pytest.mark.skip("NDEV-3453")
    def test_scheduled_trx_send_tokens_to_neon_chain_contract(
        self, neon_user, evm_loader, event_caller_contract, web3_client_sol, treasury_pool
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("indexedArgs()")
        value = 100000
        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            value=value,
            target=event_caller_contract.address,
            call_data=call_data,
        )
        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])
        web3_client_sol.send_scheduled_transaction(tx0)
        receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash())
        event_logs = event_caller_contract.events.IndexedArgs().process_receipt(receipt)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 2
        assert event_logs[0].args.who == neon_user.checksum_address
        assert event_logs[0].args.value == value
        assert event_logs[0].event == "IndexedArgs"

    def test_scheduled_trx_send_tokens_to_sol_chain_contract(
        self, neon_user, evm_loader, event_caller_sol_chain, web3_client_sol, treasury_pool
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("indexedArgs()")
        value = 100000
        tx0 = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index=0,
            value=value,
            target=event_caller_sol_chain.address,
            call_data=call_data,
        )
        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])
        web3_client_sol.send_scheduled_transaction(tx0)
        receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash())
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

        gas_limit = 30000000
        max_fee_per_gas = 3000000000
        max_priority_fee_per_gas = 2500000000
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
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(trxs[0], 1, 0)
        if trx_count > 2:
            for i in range(1, trx_count - 1):
                tree_acc_data.add_trx(trxs[i], i + 1, 1)
        tree_acc_data.add_trx(trxs[trx_count - 1], 0xFFFF, 1)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])
        web3_client_sol.send_all_scheduled_transactions(trxs)
        receipt = web3_client_sol.wait_for_transaction_receipt(trxs[trx_count - 1].hash())
        assert receipt["status"] == 1
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        event_logs = contract.events.DataAdded().process_receipt(receipt)
        added_timestamp = event_logs[0]["args"]["timestamp"]

        assert added_timestamp <= int(tx_block_timestamp, 16)
        assert contract.functions.getDataFromMapping(added_timestamp).call() == [v1, v2]

    def test_scheduled_trx_with_small_gas_limit(
        self,
        block_timestamp_contract,
        web3_client_sol,
        neon_user,
        treasury_pool,
        evm_loader,
        event_caller_contract
    ):
        contract, _ = block_timestamp_contract

        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        call_data = abi.function_signature_to_4byte_selector("addDataToMapping(uint256,uint256)") + eth_abi.encode(
            ["uint256", "uint256"], [1, 2]
        )
        gas_limit = 3000000
        max_fee_per_gas = 3000000000
        max_priority_fee_per_gas = 2500000000

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
        )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"])
        web3_client_sol.send_scheduled_transaction(tx0)
        receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash())
        # for now, it is not possible to see error through the proxy
        assert receipt["status"] == 0
