import json
import pathlib
import random

from jsonschema import Draft4Validator

import allure
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.tracer.test_tracer_historical_methods import call_storage
from utils.helpers import wait_condition

SCHEMAS = "./integration/tests/tracer/schemas/"


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug methods check")
class TestTracerDebugMethods(BaseMixin):

    def get_schema(self, file_name):
        with open(pathlib.Path(SCHEMAS, file_name)) as f:
            d = json.load(f)
            return d

    def validate_response_result(self, response):
        schema = self.get_schema("debug_traceCall.json")
        validator = Draft4Validator(schema)
        assert validator.is_valid(response["result"])

    def test_debug_trace_call_invalid_params(self):
        response = self.tracer_api.send_rpc(
            method="debug_traceCall", params=[{}, "0x0"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == "neon_api::trace failed"

    def test_debug_trace_call_empty_params_valid_block(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = receipt["transactionHash"].hex()

        wait_condition(lambda: self.tracer_api.send_rpc(method="eth_getTransactionByHash", params=[
                       tx_hash])['result'] is not None, timeout_sec=120)
        tx_info = self.tracer_api.send_rpc(
            method="eth_getTransactionByHash", params=[tx_hash])
    
        response = self.tracer_api.send_rpc(
            method="debug_traceCall", params=[{}, tx_info["result"]["blockNumber"]])
        
        assert "error" not in response, "Error in response"
        assert response["result"]["returnValue"] == "" 
        self.validate_response_result(response)

    def test_debug_trace_call_zero_eth_call(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = receipt["transactionHash"].hex()

        wait_condition(lambda: self.tracer_api.send_rpc(method="eth_getTransactionByHash", params=[
                       tx_hash])['result'] is not None, timeout_sec=120)
        tx_info = self.tracer_api.send_rpc(
            method="eth_getTransactionByHash", params=[tx_hash])

        params = [{
            "to": tx_info["result"]["to"],
            "from": tx_info["result"]["from"],
            "gas": tx_info["result"]["gas"],
            "gasPrice": tx_info["result"]["gasPrice"],
            "value": tx_info["result"]["value"],
            "data": tx_info["result"]["input"],
        },
            tx_info["result"]["blockNumber"]
        ]

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_traceCall",
                                                        params=params)["result"] is not None,
                       timeout_sec=120)
        response = self.tracer_api.send_rpc(
            method="debug_traceCall", params=params)
        assert "error" not in response, "Error in response"
        assert response["result"]["returnValue"] == "" 
        self.validate_response_result(response)

    def test_debug_trace_call_non_zero_eth_call(self, storage_contract):
        store_value = random.randint(1, 100)
        _, _, receipt = call_storage(
            self, storage_contract, store_value, "blockNumber")
        tx_hash = receipt["transactionHash"].hex()

        wait_condition(lambda: self.tracer_api.send_rpc(method="eth_getTransactionByHash", params=[
                       tx_hash])['result'] is not None, timeout_sec=120)
        tx_info = self.tracer_api.send_rpc(
            method="eth_getTransactionByHash", params=[tx_hash])

        params = [{
            "to": tx_info["result"]["to"],
            "from": tx_info["result"]["from"],
            "gas": tx_info["result"]["gas"],
            "gasPrice": tx_info["result"]["gasPrice"],
            "value": tx_info["result"]["value"],
            "data": tx_info["result"]["input"],
        },
            tx_info["result"]["blockNumber"]
        ]

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_traceCall",
                                                        params=params)["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_traceCall", params=params)
        assert "error" not in response, "Error in response"
        assert 1 <= int(response["result"]["returnValue"]) <= 100
        self.validate_response_result(response)

    def test_debug_transaction_call(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = receipt["transactionHash"].hex()

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_traceTransaction",
                                                        params=[tx_hash])["result"] is not None,
                       timeout_sec=120)
        response = self.tracer_api.send_rpc(
            method="debug_traceTransaction", params=[tx_hash])
        assert "error" not in response, "Error in response"
        self.validate_response_result(response)

    def test_debug_trace_block_by_number(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = receipt["transactionHash"].hex()

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_traceBlockByNumber",
                                                        params=[hex(receipt["blockNumber"])])["result"] is not None,
                       timeout_sec=120)
        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByNumber", params=[hex(receipt["blockNumber"])])
        assert "error" not in response, "Error in response"
        assert tx_hash == response["result"][0]["txHash"]
        self.validate_response_result(response["result"][0])

    def test_debug_trace_block_by_hash(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_block = hex(receipt["blockNumber"])

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_traceBlockByHash",
                                                        params=[receipt["transactionHash"].hex()])["result"] is not None,
                       timeout_sec=120)
        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByHash", params=[receipt["transactionHash"].hex()])
        assert "error" not in response, "Error in response"
        assert tx_block == response["result"][0]["txNumber"]

        self.validate_response_result(response["result"][0])
