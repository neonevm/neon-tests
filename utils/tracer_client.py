import allure
from web3.types import TxData

from utils.apiclient import JsonRPCSession
from utils.helpers import wait_condition


class TracerClient:
    def __init__(self, url):
        self.url = url
        self.tracer_api = JsonRPCSession(url)

    @allure.step("send rpc and wait response")
    def send_rpc_and_wait_response(self, method_name, params, req_type=None, timeout_sec: int = 120):
        return wait_condition(
            func_cond=lambda: self.tracer_api.send_rpc(method=method_name, params=params, req_type=req_type),
            check_success=lambda r: r.get("result", None) is not None,
            timeout_sec=timeout_sec,
        )

    def send_rpc(self, method, params, req_type=None):
        return self.tracer_api.send_rpc(method=method, params=params, req_type=req_type)

    @allure.step("send rpc debug_traceCall")
    def debug_trace_call(self, tx_data: TxData):
        params = [
            {
                "to": tx_data["to"],
                "from": tx_data["from"],
                "gas": hex(tx_data["gas"]),
                "gasPrice": hex(tx_data["gasPrice"]),
                "value": hex(tx_data["value"]),
                "data": "0x" + tx_data["input"].hex(),
            },
            hex(tx_data["blockNumber"]),
        ]
        response = self.send_rpc_and_wait_response("debug_traceCall", params)

        return response

    @allure.step("send rpc debug_traceTransaction")
    def debug_trace_transaction(
        self,
        tx_hash: str,
        tracer_type: str = "",
        with_log=False,
        only_top_call=False,
        wait_response: int = 120,
    ):
        params = [tx_hash]
        if tracer_type or with_log or only_top_call:
            cfg = {"withLog": with_log, "OnlyTopCall": only_top_call}
            params.append({"tracer": tracer_type, "tracerConfig": cfg})

        return self.send_rpc_and_wait_response("debug_traceTransaction", params, timeout_sec=wait_response)

    @allure.step("send rpc debug_traceBlockByHash or debug_traceBlockByNumber")
    def debug_trace_block_by_hash_or_number(
        self,
        req_type: str,
        block_hash_or_number: str,
        tracer_type: str = "",
        with_log=False,
        only_top_call=False,
    ):

        params = [block_hash_or_number]
        if tracer_type or with_log or only_top_call:
            cfg = {"withLog": with_log, "OnlyTopCall": only_top_call}
            params.append({"tracer": tracer_type, "tracerConfig": cfg})

        if req_type == "hash":
            method = "debug_traceBlockByHash"
        else:
            method = "debug_traceBlockByNumber"
        response = self.send_rpc_and_wait_response(method, params)
        return response

    @allure.step("send rpc debug_getRawHeader")
    def debug_get_raw_header_by_block_hash_or_number(self, block_hash_or_number: str):
        """block_hash_or_number - block number or block hash in hex format"""
        params = [block_hash_or_number]
        response = self.send_rpc_and_wait_response("debug_getRawHeader", params)
        return response

    @allure.step("send rpc debug_getModifiedAccounts")
    def debug_get_modified_accounts_by_block_hashes_or_numbers(
        self, block_hashes_or_numbers: list[str], param_type="hash"
    ):
        """block_hashes_or_numbers - blocks number or block hash in hex format"""
        params = block_hashes_or_numbers
        if param_type == "number":
            method = "debug_getModifiedAccountsByNumber"
        else:
            method = "debug_getModifiedAccountsByHash"
        response = self.send_rpc_and_wait_response(method, params)
        return response

    @allure.step("send rpc debug_getRawTransaction")
    def debug_get_raw_transaction(
        self,
        tx_hash: str,
        timeout_sec: int = 0,
    ):
        params = [tx_hash]
        if timeout_sec:
            response = self.send_rpc_and_wait_response("debug_getRawTransaction", params, timeout_sec=timeout_sec)
        else:
            response = self.send_rpc("debug_getRawTransaction", params)
        return response

    @allure.step("send rpc eth_call")
    def eth_call(
        self,
        tx_data: TxData,
        is_prestate=False,
        is_tx_block=False,
        overrides_param: dict = None,
    ):
        if is_tx_block:
            block_number = hex(tx_data["blockNumber"])
        else:
            block_number = hex(tx_data["blockNumber"] - 1)

        params = [
            {
                "from": tx_data["from"],
                "to": tx_data["to"],
                "gas": hex(tx_data["gas"]),
                "gasPrice": hex(tx_data["gasPrice"]),
                "value": hex(tx_data["value"]),
                "data": "0x" + tx_data["input"].hex(),
            },
            block_number,
        ]

        if is_prestate:
            params.append({"tracer": "prestateTracer"})
        if overrides_param is not None:
            params.append(overrides_param)
        response = self.send_rpc_and_wait_response("eth_call", params)

        return response

    @allure.step("send rpc eth_getStorageAt")
    def eth_get_storage_at(
        self,
        storage_address: str,
        position: str,
        request_type: str,
        request_value,
    ):
        params = [storage_address, position, {request_type: request_value}]
        response = self.send_rpc_and_wait_response("eth_getStorageAt", params, request_type)
        return response

    @allure.step("send rpc eth_getTransactionCount")
    def eth_get_transaction_count(
        self,
        sender_address: str,
        request_type: str,
        request_value,
    ):
        params = [sender_address, {request_type: request_value}]
        response = self.send_rpc_and_wait_response("eth_getTransactionCount", params, request_type)
        return response

    @allure.step("send rpc eth_getBalance")
    def eth_get_balance(
        self,
        sender_address: str,
        request_type: str,
        request_value,
    ):
        params = [sender_address, {request_type: request_value}]
        response = self.send_rpc_and_wait_response("eth_getBalance", params, request_type)
        return response

    @allure.step("send rpc eth_getCode")
    def eth_get_code(
        self,
        contract_address: str,
        request_type: str,
        request_value,
    ):
        params = [contract_address, {request_type: request_value}]
        response = self.send_rpc_and_wait_response("eth_getCode", params, request_type)
        return response

    @allure.step("send rpc get_neon_revision")
    def get_neon_revision(self, block: int):
        response = self.tracer_api.send_rpc(method="get_neon_revision", params=block)
        return response

    @allure.step("send rpc trace_transaction")
    def trace_transaction(self, tx_hash: str):
        response = self.send_rpc_and_wait_response(method_name="trace_transaction", params=[tx_hash])
        return response
