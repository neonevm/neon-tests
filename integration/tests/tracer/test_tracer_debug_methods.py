import json
import pathlib
import random
import re

from jsonschema import Draft4Validator
from rlp import decode
from rlp.sedes import List, big_endian_int, binary

import allure
import pytest

from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient
from utils.helpers import padhex


SCHEMAS = "./integration/tests/tracer/schemas/"
GOOD_CALLDATA = ["0x60fe60005360016000f3"]


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug methods check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestTracerDebugMethods:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient

    def get_schema(self, file_name):
        with open(pathlib.Path(SCHEMAS, file_name)) as f:
            d = json.load(f)
            return d

    def validate_response_result(self, response):
        schema = self.get_schema("debug_traceCall.json")
        validator = Draft4Validator(schema)
        assert validator.is_valid(response["result"])

   # NDEV-3009
    def test_debug_trace_call_invalid_params(self):
        response = self.tracer_api.send_rpc(method="debug_traceCall", params=[{}, "0x0"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == "neon_api::trace failed"
    
    def test_debug_trace_call_empty_params_valid_block(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = receipt["transactionHash"].hex()

        tx_info = self.web3_client.get_transaction_by_hash(tx_hash)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", [{}, hex(tx_info["blockNumber"])])

        assert "error" not in response, "Error in response"
        assert response["result"]["failed"] == False
        assert response["result"]["returnValue"] == ""

    def test_debug_trace_call_zero_eth_call(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        tx_info = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        params = [
            {
                "to": tx_info["to"],
                "from": tx_info["from"],
                "gas": hex(tx_info["gas"]),
                "gasPrice": hex(tx_info["gasPrice"]),
                "value": hex(tx_info["value"]),
                "data": tx_info["input"].hex(),
            },
            hex(tx_info["blockNumber"]),
        ]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert "result" in response
        assert response["result"]["returnValue"] == ""
        self.validate_response_result(response)

    def test_debug_trace_call_non_zero_eth_call(self, storage_object):
        sender_account = self.accounts[0]
        store_value = random.randint(1, 100)
        _, _, receipt = storage_object.call_storage(sender_account, store_value, "blockNumber")
       
        tx_info = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        params = [
            {
                "to": tx_info["to"],
                "from": tx_info["from"],
                "gas": hex(tx_info["gas"]),
                "gasPrice": hex(tx_info["gasPrice"]),
                "value": hex(tx_info["value"]),
                "data": tx_info["input"].hex(),
            },
            hex(tx_info["blockNumber"]),
        ]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(store_value), 64)[2:]
        self.validate_response_result(response)

    def test_debug_trace_transaction(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", [receipt["transactionHash"].hex()])
        assert "error" not in response, "Error in response"
        self.validate_response_result(response)

    def test_debug_trace_transaction_non_zero_trace(self, storage_object):
        sender_account = self.accounts[0]
        store_value = random.randint(1, 100)
        _, _, receipt = storage_object.call_storage(sender_account, store_value, "blockNumber")

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", [receipt["transactionHash"].hex()])

        assert "error" not in response, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(store_value), 64)[2:]
        self.validate_response_result(response)

    # GETH: NDEV-3251
    def test_debug_trace_transaction_hash_without_prefix(self, storage_object):
        sender_account = self.accounts[0]
        store_value = random.randint(1, 100)
        _, _, receipt = storage_object.call_storage(sender_account, store_value, "blockNumber")

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", [receipt["transactionHash"].hex()[2:]])

        assert "error" not in response, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(store_value), 64)[2:]
        self.validate_response_result(response)

    @pytest.mark.parametrize("hash", [6, "0x0", "", "f23e554"])
    # GETH: NDEV-3250
    def test_debug_trace_transaction_invalid_hash(self, hash):
        response = self.tracer_api.send_rpc(method="debug_traceTransaction", params=[hash])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def test_debug_trace_block_by_number(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = receipt["transactionHash"].hex()

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceBlockByNumber", [hex(receipt["blockNumber"])])
        assert "error" not in response, "Error in response"
        assert tx_hash in map(lambda v: v["txHash"], response["result"])
        self.validate_response_result(response["result"][0])

    @pytest.mark.parametrize("number", [190, "", "3f08", "num", "0x"])
    # GETH: NDEV-3250
    def test_debug_trace_block_by_invalid_number(self, number):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(method="debug_traceBlockByNumber", params=[number])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    # GETH: NDEV-3249
    @pytest.mark.skip(reason="NDEV-3249")
    def test_debug_trace_block_by_zero_number(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(method="debug_traceBlockByNumber", params=["0x0"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32000, "Invalid error code"
        assert response["error"]["message"] == "genesis is not traceable"

    def test_debug_trace_block_by_non_zero_early_number(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        wait_condition(
            lambda: self.web3_client.get_block_number() is not None,
            timeout_sec=10,
        )
        block = self.web3_client.get_block_number() - 100

        response = self.tracer_api.send_rpc(method="debug_traceBlockByNumber", params=[hex(block)])
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] == [], "Result is not empty"

    def test_debug_trace_block_by_hash(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = receipt["transactionHash"].hex()

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceBlockByHash", [receipt["blockHash"].hex()])
        assert "error" not in response, "Error in response"
        assert tx_hash in map(lambda v: v["txHash"], response["result"])

        self.validate_response_result(response["result"][0])

    @pytest.mark.parametrize("hash", [190, "0x0", "", "0x2ee1", "num", "f0918e"])
    # GETH: NDEV-3250
    def test_debug_trace_block_by_invalid_hash(self, hash):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(method="debug_traceBlockByHash", params=[hash])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    # GETH: NDEV-3249
    def test_debug_trace_block_by_non_existent_hash(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(
            method="debug_traceBlockByHash",
            params=["0xd97ff4869d52c4add6f5bcb1ba96020dd7877244b4cbf49044f49f002015ea85"],
        )
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert (
            response["error"]["message"]
            == "eth_getBlockByHash failed for '\"0xd97ff4869d52c4add6f5bcb1ba96020dd7877244b4cbf49044f49f002015ea85\"' block"
        )

    def decode_raw_header(self, header: bytes):
        sedes = List([big_endian_int, binary, binary, binary, binary])
        return decode(header, sedes)

    # NDEV-3261: incomplete header in response
    def test_debug_getRawHeader_by_block_number(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc_and_wait_response("debug_getRawHeader", [hex(receipt["blockNumber"])])
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] is not None
        header = self.decode_raw_header(bytes.fromhex(response["result"]))
        block_info = self.web3_client.eth.get_block(receipt["blockNumber"])
        assert header[0] == block_info["number"]
        assert header[1].hex() == ""
        assert header[2].hex() == block_info["parentHash"].hex()[2:]
        assert header[3].hex() == block_info["stateRoot"].hex()[2:]
        assert header[4].hex() == block_info["receiptsRoot"].hex()[2:]

    # GETH: NDEV-3250
    def test_debug_getRawHeader_by_invalid_block_number(self):
        response = self.tracer_api.send_rpc(method="debug_getRawHeader", params=["0f98e"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    # NDEV-3261: incomplete header in response
    def test_debug_getRawHeader_by_block_hash(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc_and_wait_response("debug_getRawHeader", [receipt["blockHash"].hex()])
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] is not None

        header = self.decode_raw_header(bytes.fromhex(response["result"]))
        block_info = self.web3_client.eth.get_block(receipt["blockNumber"])
        assert header[0] == block_info["number"]
        assert header[1].hex() == ""
        assert header[2].hex() == block_info["parentHash"].hex()[2:]
        assert header[3].hex() == block_info["stateRoot"].hex()[2:]
        assert header[4].hex() == block_info["receiptsRoot"].hex()[2:]

    # GETH: NDEV-3250
    def test_debug_getRawHeader_by_invalid_block_hash(self):
        response = self.tracer_api.send_rpc(method="debug_getRawHeader", params=["0f98e"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def check_modified_accounts_response(self, response, expected_accounts=[]):
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] is not None and response["result"] != []
        assert isinstance(response["result"], list)

        for account in expected_accounts:
            assert account.lower() in response["result"]

        for item in response["result"]:
            assert re.match(r"\b0x[a-f0-9]{40}\b", item)

    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_same_number(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc_and_wait_response(
            "debug_getModifiedAccountsByNumber", 
            [hex(receipt["blockNumber"]), hex(receipt["blockNumber"])]
        )
        self.check_modified_accounts_response(response, [sender_account.address, recipient_account.address])

    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_only_one_number(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc_and_wait_response(
            "debug_getModifiedAccountsByNumber", 
            [hex(receipt["blockNumber"])]
        )
        self.check_modified_accounts_response(response, [sender_account.address, recipient_account.address])

    @pytest.mark.parametrize("difference", [1, 25, 49, 50])
    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_number_blocks_difference_less_or_equal_50(self, difference):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        start_number = hex(receipt["blockNumber"] - difference)
        end_number = hex(receipt["blockNumber"])

        response = self.tracer_api.send_rpc_and_wait_response(
            "debug_getModifiedAccountsByNumber", 
            [start_number, end_number]
        )
        self.check_modified_accounts_response(response, [sender_account.address, recipient_account.address])

    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_number_51_blocks_difference(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1
        start_number = hex(receipt["blockNumber"] - 51)
        end_number = hex(receipt["blockNumber"])

        response = self.tracer_api.send_rpc(
            method="debug_getModifiedAccountsByNumber", params=[start_number, end_number]
        )
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == "Requested range (51) is too big, maximum allowed range is 50 blocks"

    @pytest.mark.parametrize("params", [[1, 124], ["94f3e", 12], ["1a456", "0x0"], ["183b8e", "183b8e"]])
    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_invalid_numbers(self, params):
        response = self.tracer_api.send_rpc(method="debug_getModifiedAccountsByNumber", params=params)
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_same_hash(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc_and_wait_response(
            "debug_getModifiedAccountsByHash",
            [receipt["blockHash"].hex(), receipt["blockHash"].hex()]
        )
        self.check_modified_accounts_response(response, [sender_account.address, recipient_account.address])

    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_hash(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt_start = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        receipt_end = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt_start["status"] == 1
        assert receipt_end["status"] == 1

        response = self.tracer_api.send_rpc_and_wait_response(
            "debug_getModifiedAccountsByHash",
            [receipt_start["blockHash"].hex(), receipt_end["blockHash"].hex()]
        )
        self.check_modified_accounts_response(response, [sender_account.address, recipient_account.address])

    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_hash_contract_deployment(self, storage_contract_with_deploy_tx):
        contract = storage_contract_with_deploy_tx[0]
        receipt = storage_contract_with_deploy_tx[1]

        response = self.tracer_api.send_rpc_and_wait_response(
            "debug_getModifiedAccountsByHash", [receipt["blockHash"].hex()]
        )
        self.check_modified_accounts_response(response, [contract.address, receipt["from"]])

    @pytest.mark.parametrize(
        "params", [[1, 124], ["0x94f3e00000000800000000", 12], ["0x1a456", "0x000000000001"], ["0x183b8e", "183b8e"]]
    )
    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_invalid_hash(self, params):
        response = self.tracer_api.send_rpc(method="debug_getModifiedAccountsByHash", params=params)
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def test_debug_get_raw_transaction(self):
        sender_account = self.accounts[0]
        transaction = self.web3_client.make_raw_tx(from_=sender_account, data=GOOD_CALLDATA[0], estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)

        receipt = self.web3_client.eth.wait_for_transaction_receipt(tx)
        assert receipt["status"] == 1
        
        response = self.tracer_api.send_rpc_and_wait_response("debug_getRawTransaction", [receipt["transactionHash"].hex()])
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] == signed_tx.rawTransaction.hex()

    # GETH: NDEV-3252
    def test_debug_get_raw_transaction_invalid_tx_hash(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1
        response = self.tracer_api.send_rpc(method="debug_getRawTransaction", params=[receipt["blockHash"].hex()])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert response["error"]["message"] == f'Empty Neon transaction receipt for {receipt["blockHash"].hex()}'

    # GETH: NDEV-3252
    def test_debug_get_raw_transaction_non_existent_tx_hash(self):
        response = self.tracer_api.send_rpc(
            method="debug_getRawTransaction",
            params=["0xd9765b77e470204ae5edb1a796ab92ecb0e20fea50aeb09275aea740af7bbc69"],
        )
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert (
            response["error"]["message"]
            == "Empty Neon transaction receipt for 0xd9765b77e470204ae5edb1a796ab92ecb0e20fea50aeb09275aea740af7bbc69"
        )
