import allure
import pytest

from integration.tests.basic.helpers.errors import Error32602, Error32000
from utils.helpers import decode_function_signature, wait_condition
from utils.scheduled_trx import ScheduledTransaction, ScheduledTrxEstimateRequest


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC neon_sendRawScheduledTransaction work")
class TestNeonRPCSendRAWTransaction:

    def test_two_transactions_in_params(
        self, web3_client_sol, json_sol_rpc_client, neon_user, common_contract, evm_loader, treasury_pool
    ):
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())

        resp = json_sol_rpc_client.send_rpc(
            method="neon_sendRawScheduledTransaction", params=[tx.encode().hex(), tx.encode().hex()]
        )

        assert "error" in resp
        assert Error32602.CODE == resp["error"]["code"]
        assert Error32602.INVALID_TRANSACTIONID == resp["error"]["message"]
        assert (
            resp["error"]["data"]["errors"][0] == "Method neon_sendRawScheduledTransaction expect 1 parameters, got 2."
        )

        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

    def test_repeat_call_with_same_trx_hash(
        self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())

        web3_client_sol.send_scheduled_transaction(tx)
        web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

        resp_after_waiting = web3_client_sol.send_scheduled_transaction(tx, check_result=False)
        assert "error" in resp_after_waiting
        assert "unknown transaction hash" in resp_after_waiting["error"]["message"]

    def test_no_tree_account_for_trx(self, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool):
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        resp = web3_client_sol.send_scheduled_transaction(tx, check_result=False)
        assert "error" in resp
        assert Error32000.CODE == resp["error"]["code"]
        assert Error32000.UNKNOWN_TRANSACTION_HASH == resp["error"]["message"]

    def test_bad_chain_id_url(
        self, json_rpc_client, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool
    ):
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())

        resp = json_rpc_client.send_rpc(method="neon_sendRawScheduledTransaction", params=[tx.encode().hex()])
        assert "error" in resp
        assert Error32000.CODE == resp["error"]["code"]
        assert Error32000.WRONG_CHAIN_ID == resp["error"]["message"]

        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

    def test_bad_empty_hash_of_trx(self, json_sol_rpc_client):
        resp = json_sol_rpc_client.send_rpc(method="neon_sendRawScheduledTransaction", params=[""])
        assert "error" in resp
        assert Error32602.CODE == resp["error"]["code"]
        assert Error32602.WRONG_TRANSACTION_FORMAT == resp["error"]["message"]

    @pytest.mark.parametrize("case", ("empty_param", "broken_param"))
    def test_bad_hash_of_trx(
        self, json_sol_rpc_client, web3_client_sol, neon_user, common_contract, evm_loader, treasury_pool, case
    ):
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())
        params = None
        if case == "empty_param":
            params = [""]
        elif case == "broken_param":
            params = [tx.encode().hex() * 2]

        resp = json_sol_rpc_client.send_rpc(method="neon_sendRawScheduledTransaction", params=params)
        assert "error" in resp
        assert Error32602.CODE == resp["error"]["code"]
        assert Error32602.WRONG_TRANSACTION_FORMAT == resp["error"]["message"]

        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)
