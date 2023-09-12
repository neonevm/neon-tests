import random
import typing as tp
import allure
import json
import jsonschema
from jsonschema import Draft4Validator
import pytest
from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import wait_condition

SCHEMAS = "./integration/tests/tracer/schemas/"


@allure.story("Tracer API RPC calls debug methods check")
class TestTracerRpcCalls(BaseMixin):
    _contract: tp.Optional[tp.Any] = None

    def get_schema(self, file_name):
        with open(SCHEMAS + file_name) as f:
            d = json.load(f)
            return d

    def test_debug_trace_call(self):
        reciept = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert reciept["status"] == 1
        tx_hash = reciept["transactionHash"].hex()
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

        response = self.tracer_api.send_rpc(
            method="debug_traceCall", params=params)
        assert "error" not in response, "Error in response"

        # TODO: remove this when returnData will be an array (got null instead of array)
        # response['result']['structLogs'][0]['returnData'] = []

        schema = self.get_schema("debug_traceCall.json")
        validator = Draft4Validator(schema)

        assert validator.is_valid(response['result'])
    
    def test_debug_transaction_call(self):
        reciept = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert reciept["status"] == 1
        print(reciept)
        tx_hash = reciept["transactionHash"].hex()
       
        response = self.tracer_api.send_rpc(
            method="debug_traceTransaction", params=[tx_hash])
        assert "error" not in response, "Error in response"
        
        schema = self.get_schema("debug_traceCall.json")
        validator = Draft4Validator(schema)

        assert validator.is_valid(response['result'])
