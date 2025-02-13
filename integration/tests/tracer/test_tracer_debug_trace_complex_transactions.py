import allure
import pytest
import eth_abi

from eth_utils import abi

from utils.consts import wSOL
from utils.models.result import EthGetBlockByHashResult
from utils.scheduled_trx import ScheduledTransaction, ScheduledTrxEstimateRequest
from utils.types import TransactionType
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient
from utils.helpers import wait_condition
from tracer_helper import validate_response_result

tracer_params = {"tracer": "callTracer", "tracerConfig": {"withLog": True}}


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug method trace_transaction iterative txs check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestDebugTraceIterativeTransaction:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient

    def test_trace_iterative_tx_struct_opcode_tracer(self, counter_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)

        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        params = [receipt["transactionHash"].hex()]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)
        validate_response_result(response)

    def test_trace_iterative_tx(self, counter_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)

        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        params = [receipt["transactionHash"].hex(), tracer_params]
        print(params)
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        assert response["result"]["from"] == receipt["from"]
        assert response["result"]["to"] == receipt["to"]

    def test_trace_iterative_tx_eip_1559(self, counter_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account, tx_type=TransactionType.EIP_1559)

        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        assert response["result"]["from"] == receipt["from"]
        assert response["result"]["to"] == receipt["to"]

    def test_trace_iterative_tx_sol_chain(self, web3_client_sol, class_account_sol_chain, counter_contract_sol_chain):
        sender_account = class_account_sol_chain
        tx = web3_client_sol.make_raw_tx(from_=sender_account)

        instruction_tx = counter_contract_sol_chain.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = web3_client_sol.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: web3_client_sol.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)
        assert response["result"]["from"] == receipt["from"]
        assert response["result"]["to"] == receipt["to"]

    def test_trace_block_timestamp_iterative(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callIterativeTrx().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())

        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        event_logs = contract.events.Result().process_receipt(receipt)
        assert len(event_logs) == 1, "Event logs are not found"
        assert event_logs[0]["args"]["block_timestamp"] <= int(tx_block_timestamp, 16)

        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)
        assert response["result"]["from"] == receipt["from"]
        assert response["result"]["to"] == receipt["to"]

    def test_trace_scheduled_tx(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
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
        receipt = web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)
        pending_trx = web3_client_sol.get_pending_transactions(neon_user.checksum_address)
        assert len(pending_trx) >= 1
        assert pending_trx[hex(tx.nonce)][0]["status"] in ("Done", "InProgress")
        assert common_contract.functions.getNumber().call() == contract_data

        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)
        assert response["result"]["from"] == receipt["from"]
        assert response["result"]["to"] == receipt["to"]
