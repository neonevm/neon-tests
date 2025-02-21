import random

import allure
import eth_abi
import pytest
from eth_utils import abi
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solders.pubkey import Pubkey
from spl.token.instructions import get_associated_token_address, create_associated_token_account

from utils.consts import wSOL, LAMPORT_PER_SOL
from utils.models.result import EthGetBlockByHashResult
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest


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
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) >= 1
        assert pending_trx[hex(tx.nonce)][0]["status"] in ("Done", "InProgress")
        assert common_contract.functions.getNumber().call() == contract_data

    def test_multiple_scheduled_trx(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trx_estimate_obj_list = []
        for i in range(4):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
            )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(4):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
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
            resp = web3_client_sol.wait_for_transaction_receipt(trx.hash())
            assert resp["status"] == 1
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) >= 1
        assert pending_trx[hex(nonce)][0]["status"] == "Done"
        assert pending_trx[hex(nonce)][0]["hash"][2:] == trxs[0].hash().hex()

    def test_multiple_scheduled_trx_with_failed_trx(
        self, web3_client_sol, neon_user, treasury_pool, revert_contract_caller, event_caller_contract, evm_loader
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas

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
        resp1 = web3_client_sol.wait_for_transaction_receipt(tx0.hash())
        assert resp1["status"] == 0
        resp2 = web3_client_sol.wait_for_transaction_receipt(tx1.hash())
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

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc.data, wSOL["address_spl"], payer_nonce=nonce
        )
        with pytest.raises(AssertionError, match="transaction with the same nonce already exists"):
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
        receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash())
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

        trx_estimate_obj_list = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, contract.address, call_data[i])
            )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
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
            receipt = web3_client_sol.wait_for_transaction_receipt(trx.hash())
            assert receipt["status"] == 1
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
        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas

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
        assert receipt["status"] == 0

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
            receipt = web3_client_sol.wait_for_transaction_receipt(trx.hash())
            assert receipt["status"] == 1, f"Trx failed: receipt - {receipt}"


@allure.feature("Solana native")
@allure.story("Test sending scheduled transaction ERC20ForSplNew")
class TestScheduledTrxERC20new:

    def test_scheduled_trx_pda_balance(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)

        my_pda = Pubkey(erc20_spl_mintable_new.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())

        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        erc20_spl_mintable_new.pop_up_balance(evm_loader, recipient=neon_user, pda_amount=1000, ata_amount=1000)

        balance_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        assert (
            int(evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount) == balance_pda == 1000
        )

        data = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, 1000]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, erc20_spl_mintable_new.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)

        balance_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(neon_user.checksum_address).call()

        assert erc20_spl_mintable_new.get_balance(recipient.checksum_address) == 1000
        assert erc20_spl_mintable_new.get_balance(neon_user.checksum_address) == balance_ata == 1000

        assert int(evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount) == 0
        assert int(evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount) == 1000

    def test_scheduled_trx_no_pda_balance_uses_ata(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)

        my_pda = Pubkey(erc20_spl_mintable_new.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        erc20_spl_mintable_new.pop_up_balance(evm_loader, recipient=neon_user, pda_amount=1000, ata_amount=1000)

        assert int(evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount) == 1000

        data = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, 2000]
        )

        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        tx0 = ScheduledTransaction(
            nonce=nonce,
            index=0,
            target=erc20_spl_mintable_new.address,
            call_data=data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            payer=neon_user.checksum_address,
            sender=None,
        )

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx0.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)

        assert erc20_spl_mintable_new.get_balance(recipient.checksum_address) == 2000
        assert erc20_spl_mintable_new.get_balance(neon_user.checksum_address) == 0

        assert int(evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount) == 0
        assert int(evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount) == 0

    def test_scheduled_trx_both_pda_and_ata_used(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)
        amount_to_transfer = 1_000

        my_pda = Pubkey(erc20_spl_mintable_new.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        erc20_spl_mintable_new.pop_up_balance(
            evm_loader, recipient=neon_user, pda_amount=amount_to_transfer, ata_amount=amount_to_transfer
        )

        for account in (my_pda, my_ata):
            assert int(evm_loader.get_token_account_balance(account, commitment=Confirmed).value.amount) == 1000

        data = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, 2000]
        )

        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        tx0 = ScheduledTransaction(
            nonce=nonce,
            index=0,
            target=erc20_spl_mintable_new.address,
            call_data=data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            payer=neon_user.checksum_address,
            sender=None,
        )

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx0.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)

        balance_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        balance_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(neon_user.checksum_address).call()

        assert erc20_spl_mintable_new.get_balance(recipient.checksum_address) == 2000
        assert balance_pda == balance_ata == 0

    def test_scheduled_trx_transferSolana_ata_balance_not_used(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):

        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())

        erc20_spl_mintable_new.pop_up_balance(evm_loader, recipient=neon_user, pda_amount=5, ata_amount=2000)
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        data = abi.function_signature_to_4byte_selector("transferSolana(address,uint256)") + eth_abi.encode(
            ["bytes", "uint256"], [bytes(my_ata), 10]
        )

        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        tx0 = ScheduledTransaction(
            nonce=nonce,
            index=0,
            target=erc20_spl_mintable_new.address,
            call_data=data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            payer=neon_user.checksum_address,
            sender=None,
        )

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx0.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        resp = web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)

        assert resp["status"] == 0, resp

    @pytest.mark.xfail(reason="NDEV-3575")
    def test_multiple_transactions_with_transfer_from_solana(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):

        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        trx = Transaction()
        trx.add(
            create_associated_token_account(
                neon_user.solana_account.pubkey(), neon_user.solana_account.pubkey(), token_mint
            )
        )
        evm_loader.send_tx_and_check_status_ok(trx, neon_user.solana_account)
        amount = 1000

        erc20_spl_mintable_new.approve(erc20_spl_mintable_new.account, neon_user.checksum_address, amount)

        call_data = abi.function_signature_to_4byte_selector(
            "transferSolanaFrom(address,bytes,uint64)"
        ) + eth_abi.encode(
            ["address", "bytes", "uint64"],
            [erc20_spl_mintable_new.account.address, bytes(my_ata), amount],
        )

        gas_limit = 3_000_000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2_500_000_000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        tx = ScheduledTransaction(
            nonce=nonce,
            index=0,
            target=erc20_spl_mintable_new.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            payer=neon_user.checksum_address,
            sender=None,
        )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        tree_acc_data.add_trx(tx, 0xFFFF, 0)

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_scheduled_transaction(tx)

        resp = web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)
        assert resp["status"] == 1, resp

    def test_multiple_transactions_with_tree_actions_dependent_trx(
        self,
        web3_client_sol,
        neon_user,
        erc20_spl_mintable_new,
        evm_loader,
        treasury_pool,
        sol_client,
    ):
        # ┌───────┐  ┌──────┐
        # │ t0 ✓  ├─>┤ t2 ✓ │
        # │ s=0   │  │ s=1  │
        # └───────┘  └──────┘
        # ┌───────┐  ┌──────┐
        # │ t1 ✓  ├─>┤ t3 ✓ │
        # │ s=0   │  │ s=1  │
        # └───────┘  └──────┘
        recipient = NeonUser(evm_loader.loader_id)  # Recipient #1

        erc20_spl_mintable_new.approve(erc20_spl_mintable_new.account, neon_user.checksum_address, 800)

        top_up_in_trx = 400
        amount_to_recipient = 400

        data_0 = data_1 = abi.function_signature_to_4byte_selector(
            "transferFrom(address,address,uint256)"
        ) + eth_abi.encode(
            ["address", "address", "uint256"],
            [erc20_spl_mintable_new.account.address, neon_user.checksum_address, top_up_in_trx],
        )

        data_2 = data_3 = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, amount_to_recipient]
        )

        call_data: list = [data_0, data_1, data_2, data_3]

        # TODO Use estimate result method to count transaction fees. Waiting for developers to fix it.

        gas_limit = 3_000_000
        trx_count = 4
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2_500_000_000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        trxs = []
        for i in range(trx_count):
            trxs.append(
                ScheduledTransaction(
                    nonce=nonce,
                    index=i,
                    target=erc20_spl_mintable_new.address,
                    call_data=call_data[i],
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                    gas_limit=gas_limit,
                    payer=neon_user.checksum_address,
                    sender=None,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            assert (
                web3_client_sol.wait_for_transaction_receipt(trx.hash(), timeout=180)["status"] == 1
            ), f"transaction_{trx.index} failed"

        balance_user_1 = erc20_spl_mintable_new.get_balance(neon_user.checksum_address)
        balance_user_2 = erc20_spl_mintable_new.get_balance(recipient.checksum_address)

        balance_user_1_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        balance_user_1_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(neon_user.checksum_address).call()
        balance_user_2_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(recipient.checksum_address).call()
        balance_user_2_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(recipient.checksum_address).call()

        assert balance_user_1 == balance_user_1_ata == balance_user_1_pda == 0
        assert balance_user_2_ata == 0
        assert balance_user_2 == balance_user_2_pda == 800

    def test_multiple_transactions_with_tree_actions_independent(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):

        recipient = NeonUser(evm_loader.loader_id)

        amount_to_transfer = 1_000

        my_pda = Pubkey(erc20_spl_mintable_new.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        erc20_spl_mintable_new.pop_up_balance(
            evm_loader, recipient=neon_user, pda_amount=amount_to_transfer, ata_amount=amount_to_transfer
        )

        assert (
            int(evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount) == amount_to_transfer
        )
        assert (
            int(evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount) == amount_to_transfer
        )

        transfer_amount = 200
        burn_amount = 100
        approve_amount = 1000
        trx_count = 4

        data_0 = abi.function_signature_to_4byte_selector("approve(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [neon_user.checksum_address, approve_amount]
        )
        data_1 = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, transfer_amount]
        )
        data_2 = abi.function_signature_to_4byte_selector("burn(uint256)") + eth_abi.encode(["uint256"], [burn_amount])
        data_3 = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, transfer_amount]
        )
        call_data: list = [data_0, data_1, data_2, data_3]

        # TODO Use estimate result method to count transaction fees. Waiting for developers to fix it.
        trx_estimate_obj_list: list[ScheduledTrxEstimateRequest] = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, erc20_spl_mintable_new.address, call_data[i])
            )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)

        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[1], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 0)

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            assert (
                web3_client_sol.wait_for_transaction_receipt(trx.hash(), timeout=180)["status"] == 1
            ), f"transaction_{trx.index} failed"

        balance_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        balance_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(neon_user.checksum_address).call()

        assert erc20_spl_mintable_new.get_balance(recipient.checksum_address) == transfer_amount * 2
        assert balance_pda == amount_to_transfer - transfer_amount * 2 - burn_amount
        assert balance_ata == amount_to_transfer
