import json
import pathlib
import random
import re

from jsonschema import Draft4Validator
from rlp import decode
from rlp.sedes import List, big_endian_int, binary

import allure
import pytest
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
        assert 1 <= int(response["result"]["returnValue"], 16) <= 100
        self.validate_response_result(response)

    def test_debug_trace_transaction(self):
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

    def test_debug_trace_transaction_non_zero_trace(self, storage_contract):
        store_value = random.randint(1, 100)
        _, _, receipt = call_storage(
            self, storage_contract, store_value, "blockNumber")
        tx_hash = receipt["transactionHash"].hex()

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_traceTransaction",
                                                        params=[tx_hash])["result"] is not None,
                       timeout_sec=120)
        response = self.tracer_api.send_rpc(
            method="debug_traceTransaction", params=[tx_hash])
        assert "error" not in response, "Error in response"
        assert "error" not in response, "Error in response"
        assert 1 <= int(response["result"]["returnValue"], 16) <= 100
        self.validate_response_result(response)

    def test_debug_trace_transaction_hash_without_prefix(self, storage_contract):
        store_value = random.randint(1, 100)
        _, _, receipt = call_storage(
            self, storage_contract, store_value, "blockNumber")
        tx_hash = receipt["transactionHash"].hex()[2:]

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_traceTransaction",
                                                        params=[tx_hash])["result"] is not None,
                       timeout_sec=120)
        response = self.tracer_api.send_rpc(
            method="debug_traceTransaction", params=[tx_hash])
        assert "error" not in response, "Error in response"
        assert "error" not in response, "Error in response"
        assert 1 <= int(response["result"]["returnValue"], 16) <= 100
        self.validate_response_result(response)

    @pytest.mark.parametrize("hash", [6, '0x0', '', 'f23e554'])
    def test_debug_trace_transaction_invalid_hash(self, hash):
        response = self.tracer_api.send_rpc(
            method="debug_traceTransaction", params=[hash])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

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
    
    @pytest.mark.parametrize("number", [190, '', '3f08', 'num', '0x'])
    def test_debug_trace_block_by_invalid_number(self, number):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByNumber", params=[number])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def test_debug_trace_block_by_zero_number(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByNumber", params=['0x0'])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == "Genesis block is not traceable"

    def test_debug_trace_block_by_non_zero_early_number(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByNumber", params=['0x2ee1'])
        assert "error" not in response, "Error in response"
        assert response["result"] == [], "Result is not empty"

    def test_debug_trace_block_by_hash(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = receipt["transactionHash"].hex()

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_traceBlockByHash",
                                                        params=[receipt["blockHash"].hex()])["result"] is not None,
                       timeout_sec=180)
        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByHash", params=[receipt["blockHash"].hex()])
        assert "error" not in response, "Error in response"
        assert tx_hash == response["result"][0]["txHash"]

        self.validate_response_result(response["result"][0])

    @pytest.mark.parametrize("hash", [190, '0x0', '', '0x2ee1', 'num', 'f0918e'])
    def test_debug_trace_block_by_invalid_hash(self, hash):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByHash", params=[hash])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def test_debug_trace_block_by_non_existent_hash(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByHash", params=['0xd97ff4869d52c4add6f5bcb1ba96020dd7877244b4cbf49044f49f002015ea85'])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == "eth_getBlockByHash returns None for '\"0xd97ff4869d52c4add6f5bcb1ba96020dd7877244b4cbf49044f49f002015ea85\"' block"

    def decode_raw_header(self, header: bytes):
        sedes = List([big_endian_int, binary, binary, binary, binary])
        return decode(header, sedes)

    def test_getRawHeader_by_block_number(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_getRawHeader",
                                                        params=[hex(receipt["blockNumber"])])["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_getRawHeader", params=[hex(receipt["blockNumber"])])
        assert "error" not in response, "Error in response"
        assert response["result"] is not None

        header = self.decode_raw_header(bytes.fromhex(response["result"]))
        block_info = self.web3_client.eth.get_block(receipt["blockNumber"])
        assert header[0] == block_info["number"]
        assert header[1].hex() == '' 
        assert header[2].hex() == block_info["parentHash"].hex()[2:]
        assert header[3].hex() == block_info["stateRoot"].hex()[2:]
        assert header[4].hex() == block_info["receiptsRoot"].hex()[2:]


    def test_getRawHeader_by_invalid_block_number(self):
        response = self.tracer_api.send_rpc(
            method="debug_getRawHeader", params=["0f98e"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"
    
    def test_getRawHeader_by_block_hash(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_getRawHeader",
                                                        params=[receipt["blockHash"].hex()])["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_getRawHeader", params=[receipt["blockHash"].hex()])
        assert "error" not in response, "Error in response"
        assert response["result"] is not None

        header = self.decode_raw_header(bytes.fromhex(response["result"]))
        block_info = self.web3_client.eth.get_block(receipt["blockNumber"])
        assert header[0] == block_info["number"]
        assert header[1].hex() == '' 
        assert header[2].hex() == block_info["parentHash"].hex()[2:]
        assert header[3].hex() == block_info["stateRoot"].hex()[2:]
        assert header[4].hex() == block_info["receiptsRoot"].hex()[2:]

    def test_getRawHeader_by_invalid_block_hash(self):
        response = self.tracer_api.send_rpc(
            method="debug_getRawHeader", params=["0f98e"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def check_modified_accounts_response(self, response):
        assert "error" not in response, "Error in response"
        assert response["result"] is not None and response["result"] != []
        assert isinstance(response["result"], list)
        assert self.sender_account.address in response["result"]
        for item in response["result"]:
            assert re.match(r'^0x[a-fA-F\d]{64}$', item) 

    @pytest.mark.skip(reason="bug NDEV-2375")
    def test_debug_get_modified_accounts_by_number(self):
        receipt_start = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        receipt_end = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt_start["status"] == 1
        assert receipt_end["status"] == 1

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_getModifiedAccountsByNumber",
                                                        params=[hex(receipt_start["blockNumber"]), hex(receipt_end["blockNumber"])])["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByNumber", params=[hex(receipt_start["blockNumber"]), hex(receipt_end["blockNumber"])])
        self.check_modified_accounts_response(response)
    
    @pytest.mark.skip(reason="bug NDEV-2375")
    def test_debug_get_modified_accounts_by_same_number(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_getModifiedAccountsByNumber",
                                                        params=[hex(receipt["blockNumber"]), hex(receipt["blockNumber"])])["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByNumber", params=[hex(receipt["blockNumber"]), hex(receipt["blockNumber"])])
        self.check_modified_accounts_response(response)
   
    @pytest.mark.skip(reason="bug NDEV-2375")
    def test_debug_get_modified_accounts_by_only_one_number(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_getModifiedAccountsByNumber",
                                                        params=[hex(receipt["blockNumber"])])["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByNumber", params=[hex(receipt["blockNumber"])])
        self.check_modified_accounts_response(response)
    
    @pytest.mark.skip(reason="bug NDEV-2375")
    @pytest.mark.parametrize("difference", [1, 50, 199, 200])
    def test_debug_get_modified_accounts_by_number_blocks_difference_less_or_equal_200(self, difference):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        start_number = hex(receipt["blockNumber"] - difference)
        end_number= hex(receipt["blockNumber"])
        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_getModifiedAccountsByNumber",
                                                        params=[start_number, end_number])["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByNumber", params=[start_number, end_number])
        self.check_modified_accounts_response(response)
    
    @pytest.mark.skip(reason="bug NDEV-2375")
    def test_debug_get_modified_accounts_by_number_201_blocks_difference(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        start_number = hex(receipt["blockNumber"] - 201)
        end_number= hex(receipt["blockNumber"])
        
        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByNumber", params=[start_number, end_number])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == "Requested range (201) is too big, maximum allowed range is 200 blocks"
    
    @pytest.mark.skip(reason="bug NDEV-2375")
    @pytest.mark.parametrize("params", [[1, 124], ["94f3e", 12], ["1a456", "0x0"], ["183b8e", "183b8e"]])
    def test_debug_get_modified_accounts_by_invalid_numbers(self, params):        
        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByNumber", params=params)
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"
    
    @pytest.mark.skip(reason="bug NDEV-2375")
    def test_debug_get_modified_accounts_by_hash(self):
        receipt_start = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        receipt_end = self.send_neon(
            self.sender_account, self.recipient_account, 0.1)
        assert receipt_start["status"] == 1
        assert receipt_end["status"] == 1

        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_getModifiedAccountsByHash",
                                                        params=[receipt_start["blockHash"].hex(), receipt_end["blockHash"].hex()])["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByHash", params=[receipt_start["blockHash"].hex(), receipt_end["blockHash"].hex()])
        self.check_modified_accounts_response(response)
    
    @pytest.mark.skip(reason="bug NDEV-2375")
    @pytest.mark.parametrize("params", [[1, 124], ["0x94f3e00000000800000000", 12], ["0x1a456", "0x000000000001"], ["0x183b8e", "183b8e"]])
    def test_debug_get_modified_accounts_by_invalid_hash(self, params):
        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByHash", params=params)
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def test_debug_get_raw_transaction(self):
        nonce = self.web3_client.get_nonce(self.sender_account.address)
        transaction = self.create_tx_object(nonce=nonce, amount=0.1)
        signed_tx = self.web3_client.eth.account.sign_transaction(
                transaction, self.sender_account.key
            )
        tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.web3_client.eth.wait_for_transaction_receipt(tx)
        assert receipt["status"] == 1
        wait_condition(lambda: self.tracer_api.send_rpc(method="debug_getRawTransaction",
                                                        params=[receipt["transactionHash"].hex()])["result"] is not None,
                       timeout_sec=120)
        
        response = self.tracer_api.send_rpc(
            method="debug_getRawTransaction", params=[receipt["transactionHash"].hex()])
        assert "error" not in response, "Error in response"
        assert response["result"] == signed_tx.rawTransaction.hex()

    def test_debug_get_raw_transaction_invalid_tx_hash(self):
        receipt = self.send_neon(self.sender_account, self.recipient_account, 0.1)
        assert receipt["status"] == 1
        response = self.tracer_api.send_rpc(method="debug_getRawTransaction", 
                                                params=[receipt["blockHash"].hex()])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == f'Empty Neon transaction receipt for {receipt["blockHash"].hex()}'

    def test_debug_get_raw_transaction_non_existent_tx_hash(self):
        response = self.tracer_api.send_rpc(method="debug_getRawTransaction", 
                                            params=["0xd9765b77e470204ae5edb1a796ab92ecb0e20fea50aeb09275aea740af7bbc69"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == '''Empty Neon transaction receipt for 
            0xd9765b77e470204ae5edb1a796ab92ecb0e20fea50aeb09275aea740af7bbc69'''
