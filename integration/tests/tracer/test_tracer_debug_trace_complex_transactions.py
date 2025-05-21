import random
import allure
import pytest
from polling2 import TimeoutException
from solana.transaction import AccountMeta, Instruction
from solders.pubkey import Pubkey

from utils.helpers import serialize_instruction
from utils.consts import COUNTER_ID
from utils.models.result import EthGetBlockByHashResult
from utils.scheduled_trx import ScheduledTransaction, ScheduledTrxEstimateRequest, CreateTreeAccMultipleData
from utils.tracer_validator import TracerValidator
from utils.types import TransactionType
from utils.web3client import NeonChainWeb3Client, BASE_MAX_PRIORITY_FEE
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient

from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from utils.helpers import wait_condition, decode_function_signature

tracer_params = {"tracer": "callTracer", "tracerConfig": {"withLog": True}}


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug method trace_transaction complex txs check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api", "tracer_validator")
class TestDebugTraceComplexTransactions:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient
    tracer_validator: TracerValidator

    def test_trace_iterative_tx_struct_opcode_tracer(self, counter_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)

        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        response = self.tracer_api.debug_trace_transaction(receipt["transactionHash"].hex())
        assert self.tracer_validator.check_tracer_struct_log(response)
        # TODO: create a template of the response and compare fileds and structure

    def test_trace_iterative_tx_simple(self, counter_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)

        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        response = self.tracer_api.debug_trace_transaction(
            tx_hash=receipt["transactionHash"].hex(),
            tracer_type="callTracer",
            with_log=True,
        )
        assert self.tracer_validator.check_call_tracer_type(response, tx_data)

    def test_trace_iterative_tx_reverted_status(self, revert_contract_caller):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = revert_contract_caller.functions.doTrivialRevertAferIterativeActions().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 0

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        response = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(response, wait_error=True)

        resp = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(),
            tracer_type="callTracer",
            with_log=True,
        )
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data, error_message="execution reverted")

    def test_trace_iterative_tx_with_erc20_for_spl(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        mint_amount1 = random.randint(10, 100000000)
        mint_amount2 = random.randint(10, 100000000)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mintMintTransferTransferMintMintTransferTransfer(
            mint_amount1, mint_amount2, acc.address
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        response = self.tracer_api.debug_trace_transaction(
            tx_hash=receipt["transactionHash"].hex(),
            tracer_type="callTracer",
            with_log=True,
        )
        assert self.tracer_validator.check_call_tracer_type(response, tx_data)

    def test_trace_iterative_tx_eip_1559(self, counter_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account, tx_type=TransactionType.EIP_1559)

        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        response = self.tracer_api.debug_trace_transaction(
            tx_hash=receipt["transactionHash"].hex(),
            tracer_type="callTracer",
            with_log=True,
        )
        assert self.tracer_validator.check_call_tracer_type(response, tx_data)

    def test_trace_iterative_tx_sol_chain(self, web3_client_sol, class_account_sol_chain, counter_contract_sol_chain):
        sender_account = class_account_sol_chain
        tx = web3_client_sol.make_raw_tx(from_=sender_account)

        instruction_tx = counter_contract_sol_chain.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = web3_client_sol.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: web3_client_sol.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        response = self.tracer_api.debug_trace_transaction(
            tx_hash=receipt["transactionHash"].hex(),
            tracer_type="callTracer",
            with_log=True,
        )
        assert self.tracer_validator.check_call_tracer_type(response, tx_data)

    def test_trace_iterative_tx_block_timestamp(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callIterativeTrx().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())

        json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        response = self.tracer_api.debug_trace_transaction(
            tx_hash=receipt["transactionHash"].hex(),
            tracer_type="callTracer",
            with_log=True,
        )
        assert self.tracer_validator.check_call_tracer_type(response, tx_data)

    def test_trace_iterative_tx_block_timestamp_struct_logger_and_call_trace(self, block_timestamp_contract):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callIterativeTrx().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        response = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(response)
        resp = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), tracer_type="callTracer", with_log=True
        )
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data)

    def test_trace_block_timestamp_in_scheduled_tx(self, block_timestamp_contract, json_rpc_client, web3_client_sol):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.logTimestamp().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        resp = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(resp)

        resp = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), tracer_type="callTracer", with_log=True
        )
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data)

        encoded_ts = resp["result"]["logs"][0]["data"]
        assert tx_block_timestamp == hex(int(encoded_ts, 16))

    def test_trace_scheduled_tx(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        contract_data = 18
        data = decode_function_signature("setNumber(uint256)", [contract_data])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])
        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())
        check_trx_is_success(web3_client_sol, evm_loader, tx.hash().hex())

        receipt = web3_client_sol.wait_for_transaction_receipt(tx.hash().hex())
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        response = self.tracer_api.debug_trace_transaction(
            tx_hash=receipt["transactionHash"].hex(),
            tracer_type="callTracer",
            with_log=True,
        )
        assert self.tracer_validator.check_call_tracer_type(response, tx_data)

    def test_trace_success_multiple_scheduled_trx(
        self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        data = decode_function_signature("setNumber(uint256)", [10])

        trx_estimate_obj_list = []
        for i in range(3):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user.checksum_address, common_contract.address, data, child_transaction=hex(3)
                )
            )
        trx_estimate_obj_list.append(
            ScheduledTrxEstimateRequest(
                neon_user.checksum_address, common_contract.address, data, child_transaction="0xFFFF"
            )
        )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(4):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 3, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 3, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)

        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for tx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, tx.hash().hex(), timeout=180)
            receipt = web3_client_sol.wait_for_transaction_receipt(tx.hash().hex())

            tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
            resp = self.tracer_api.debug_trace_call(tx_data)
            assert self.tracer_validator.check_tracer_struct_log(resp)

            resp = self.tracer_api.debug_trace_transaction(
                receipt["transactionHash"].hex(), tracer_type="callTracer", with_log=True
            )
            assert self.tracer_validator.check_call_tracer_type(resp, tx_data)

    def test_trace_failed_one_scheduled_tx(
        self, web3_client_sol, neon_user, treasury_pool, revert_contract_caller, event_caller_contract, evm_loader
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
        gas_limit = 30000000

        call_data_trx0 = decode_function_signature("doAssert()")

        tx = ScheduledTransaction(
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

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
        )
        tree_acc_data.add_trx(tx, 0xFFFF, 0)
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

        web3_client_sol.send_all_scheduled_transactions([tx])

        receipt = web3_client_sol.wait_for_transaction_receipt(tx.hash().hex())
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        resp = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(resp, wait_error=True)

        resp = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), tracer_type="callTracer", with_log=True
        )
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data, error_message="execution reverted")

    def test_trace_failed_multiply_scheduled_tx(
        self, web3_client_sol, neon_user, treasury_pool, revert_contract_caller, event_caller_contract, evm_loader
    ):
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
        max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
        gas_limit = 30000000

        call_data_trx0 = decode_function_signature("doAssert()")
        call_data_trx1 = decode_function_signature("indexedArgs()")

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
        evm_loader.create_tree_account_multiple(neon_user, treasury_pool, tree_acc_data.data)

        web3_client_sol.send_all_scheduled_transactions([tx0, tx1])

        receipt = web3_client_sol.wait_for_transaction_receipt(tx0.hash().hex())
        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        resp = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(resp, wait_error=True)

        resp = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), tracer_type="callTracer", with_log=True
        )
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data, error_message="execution reverted")

        params = [tx1.hash().hex(), tracer_params]
        with pytest.raises(TimeoutException) as exc_info:
            self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        assert "Tracing Skip Scheduled Transaction is not supported" in str(exc_info.value)

    def test_trace_solana_interoperability_contract(
        self, call_solana_caller, counter_resource_address: bytes, pytestconfig
    ):
        sender = self.accounts[0]
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.executeWithGetReturnData(lamports, serialized).build_transaction(
            tx
        )

        receipt = self.web3_client.send_transaction(sender, instruction_tx)

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        resp = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(resp)

        resp = self.tracer_api.debug_trace_transaction(receipt["transactionHash"].hex(), tracer_type="callTracer")
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data)

    def test_trace_solana_interoperability_iterative_actions_and_multiple_solana_calls(
        self, counter_resource_address: bytes, call_solana_caller
    ):
        iterations = 20
        solana_calls = 5
        lamports = 0

        call_params = []
        sender = self.accounts[0]
        for _ in range(solana_calls):
            instruction = Instruction(
                program_id=COUNTER_ID,
                accounts=[
                    AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
                ],
                data=bytes([0x1]),
            )
            serialized = serialize_instruction(COUNTER_ID, instruction)
            call_params.append((lamports, serialized))

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.batchExecuteInIterativeMode(
            iterations, call_params
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=60,
        )

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        resp = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(resp, tx_data)

        resp = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), tracer_type="callTracer", with_log=True
        )
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data)

    def test_trace_failed_iterative_tx(self, expected_error_checker):
        contract = expected_error_checker
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=10000000)
        instruction_tx = contract.functions.runLoopWithZeroDivision().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 0

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        resp = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(resp, wait_error=True)

        resp = self.tracer_api.debug_trace_transaction(
            receipt["transactionHash"].hex(), tracer_type="callTracer", with_log=True
        )
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data, error_message="execution reverted")

    def test_cancel_during_iterative_transaction(self, canceled_iterative_tx_with_hash_receipt, json_rpc_client):
        neon_tx_receipt = json_rpc_client.get_neon_trx_receipt(
            canceled_iterative_tx_with_hash_receipt["transactionHash"]
        )
        assert (
            neon_tx_receipt["result"]["solanaTransactions"][-1]["solanaInstructions"][0]["neonLogs"][0]["neonEventType"]
            == "Cancel"
        )

        # TODO NDEV-3772
        # tx_data = self.web3_client.get_transaction_by_hash(
        #     canceled_iterative_tx_with_hash_receipt["transactionHash"].hex()
        # )
        # trace_call_resp = self.tracer_api.debug_trace_call(tx_data)
        # assert self.tracer_validator.check_tracer_struct_log(trace_call_resp, wait_error=True)

        dtt_resp = self.tracer_api.debug_trace_transaction(
            canceled_iterative_tx_with_hash_receipt["transactionHash"].hex()
        )
        assert dtt_resp["result"]["failed"], f'Expected failed to be True, got {dtt_resp["result"]["failed"]}'
        assert (
            len(dtt_resp["result"]["structLogs"]) == 0
        ), f'Expected empty structLogs, got {dtt_resp["result"]["structLogs"]}'

        call_tracer_resp = self.tracer_api.debug_trace_transaction(
            canceled_iterative_tx_with_hash_receipt["transactionHash"].hex(), tracer_type="callTracer", with_log=True
        )
        assert call_tracer_resp["result"]["from"].lower() == "0x0000000000000000000000000000000000000000"
        assert call_tracer_resp["result"]["input"].lower() == "0x"
        assert call_tracer_resp["result"]["type"] == "STOP"
