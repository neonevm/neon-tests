import random
import re

from rlp import decode
from rlp.sedes import List, big_endian_int, binary

import allure
import pytest

from utils.helpers import wait_condition
from utils.tracer_validator import TracerValidator
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient
from utils.helpers import padhex
from utils.tracer_validator import validate_response_result

SCHEMAS = "./integration/tests/tracer/schemas/"
GOOD_CALLDATA = ["0x60fe60005360016000f3"]


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug methods check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api", "tracer_validator")
class TestTracerDebugMethods:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient
    tracer_validator: TracerValidator

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
        tx_data = self.web3_client.get_transaction_by_hash(tx_hash)
        response = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(
            tracer_response=response, wait_error=False, return_value="", validation=False
        )

    def test_debug_trace_call_zero_eth_call(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        tx_hash = receipt["transactionHash"].hex()
        tx_data = self.web3_client.get_transaction_by_hash(tx_hash)
        response = self.tracer_api.debug_trace_call(tx_data)

        assert self.tracer_validator.check_tracer_struct_log(
            tracer_response=response, wait_result=True, wait_error=False, return_value="", validation=True
        )

    def test_debug_trace_call_non_zero_eth_call(self, storage_object):
        sender_account = self.accounts[0]
        store_value = random.randint(1, 100)
        _, _, receipt = storage_object.call_storage(sender_account, store_value, "blockNumber")

        tx_data = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        response = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(
            tracer_response=response,
            wait_result=True,
            wait_error=False,
            return_value=padhex(hex(store_value), 64)[2:],
            validation=True,
        )

    def test_debug_trace_transaction(self, send_neon_tx_receipt, tracer_api):
        tx_hash = send_neon_tx_receipt["transactionHash"].hex()
        response = self.tracer_api.debug_trace_transaction(tx_hash, wait_response=120)
        assert "error" not in response, "Error in response"
        validate_response_result(response)

    def test_debug_trace_transaction_non_zero_trace(self, call_storage_tx_receipt):
        call_storage_tx_receipt, store_value = call_storage_tx_receipt
        response = self.tracer_api.debug_trace_transaction("0x" + call_storage_tx_receipt["transactionHash"].hex())
        assert self.tracer_validator.check_tracer_struct_log(
            tracer_response=response,
            wait_result=True,
            wait_error=False,
            return_value=padhex(hex(store_value), 64)[2:],
            validation=True,
        )

    def test_debug_trace_transaction_hash_without_prefix(self, call_storage_tx_receipt):
        call_storage_tx_receipt, store_value = call_storage_tx_receipt
        response = self.tracer_api.debug_trace_transaction(call_storage_tx_receipt["transactionHash"].hex())
        assert self.tracer_validator.check_tracer_struct_log(
            tracer_response=response,
            wait_result=True,
            wait_error=False,
            return_value=padhex(hex(store_value), 64)[2:],
            validation=True,
        )

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

        response = self.tracer_api.debug_trace_block_by_hash_or_number(
            req_type="number", block_hash_or_number=hex(receipt["blockNumber"])
        )

        tx_hash = "0x" + receipt["transactionHash"].hex()
        assert tx_hash in map(lambda v: v["txHash"], response["result"])
        assert self.tracer_validator.check_tracer_struct_log(
            tracer_response=response["result"][0], wait_result=True, wait_error=False, return_value="", validation=True
        )

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

        response = self.tracer_api.debug_trace_block_by_hash_or_number(
            req_type="number", block_hash_or_number=hex(block)
        )
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] == [], "Result is not empty"

    def test_debug_trace_block_by_hash(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1
        tx_hash = "0x" + receipt["transactionHash"].hex()

        response = self.tracer_api.debug_trace_block_by_hash_or_number(
            req_type="hash", block_hash_or_number=receipt["blockHash"].hex()
        )

        assert "error" not in response, "Error in response"
        assert tx_hash in map(lambda v: v["txHash"], response["result"])

        validate_response_result(response["result"][0])

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

        response = self.tracer_api.debug_get_raw_header_by_block_hash_or_number(hex(receipt["blockNumber"]))
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] is not None
        header = self.decode_raw_header(bytes.fromhex(response["result"]))
        block_info = self.web3_client.eth.get_block(receipt["blockNumber"])
        assert header[0] == block_info["number"]
        assert header[1].hex() == ""
        assert header[2].hex() == block_info["parentHash"].hex()
        assert header[3].hex() == block_info["stateRoot"].hex()
        assert header[4].hex() == block_info["receiptsRoot"].hex()

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

        response = self.tracer_api.debug_get_raw_header_by_block_hash_or_number("0x" + receipt["blockHash"].hex())
        assert "error" not in response, "Error in response"
        assert "result" in response and response["result"] is not None

        header = self.decode_raw_header(bytes.fromhex(response["result"]))
        block_info = self.web3_client.eth.get_block(receipt["blockNumber"])
        assert header[0] == block_info["number"]
        assert header[1].hex() == ""
        assert header[2].hex() == block_info["parentHash"].hex()
        assert header[3].hex() == block_info["stateRoot"].hex()
        assert header[4].hex() == block_info["receiptsRoot"].hex()

    # GETH: NDEV-3250
    def test_debug_getRawHeader_by_invalid_block_hash(self):
        response = self.tracer_api.send_rpc(method="debug_getRawHeader", params=["0f98e"])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    @staticmethod
    @allure.step("Check modified accounts response")
    def check_modified_accounts_response(response, expected_accounts=[]):
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

        response = self.tracer_api.debug_get_modified_accounts_by_block_hashes_or_numbers(
            [hex(receipt["blockNumber"]), hex(receipt["blockNumber"])], "number"
        )
        self.check_modified_accounts_response(response, [sender_account.address, recipient_account.address])

    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_only_one_number(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        assert receipt["status"] == 1

        response = self.tracer_api.debug_get_modified_accounts_by_block_hashes_or_numbers(
            [hex(receipt["blockNumber"])], "number"
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

        response = self.tracer_api.debug_get_modified_accounts_by_block_hashes_or_numbers(
            [start_number, end_number], "number"
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

        response = self.tracer_api.debug_get_modified_accounts_by_block_hashes_or_numbers(
            [receipt["blockHash"].hex(), receipt["blockHash"].hex()], "hash"
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

        response = self.tracer_api.debug_get_modified_accounts_by_block_hashes_or_numbers(
            [receipt_start["blockHash"].hex(), receipt_end["blockHash"].hex()], "hash"
        )
        self.check_modified_accounts_response(response, [sender_account.address, recipient_account.address])

    # GETH: NDEV-3248
    def test_debug_get_modified_accounts_by_hash_contract_deployment(self, storage_contract_with_deploy_tx):
        contract = storage_contract_with_deploy_tx[0]
        receipt = storage_contract_with_deploy_tx[1]

        response = self.tracer_api.debug_get_modified_accounts_by_block_hashes_or_numbers(
            [receipt["blockHash"].hex()], "hash"
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

    # GETH: NDEV-3252
    def test_debug_get_raw_transaction_invalid_tx_hash(self, send_neon_tx_receipt):
        receipt = send_neon_tx_receipt
        response = self.tracer_api.send_rpc(method="debug_getRawTransaction", params=[receipt["blockHash"].hex()])
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"

        blockhash = "".join(["0x", receipt["blockHash"].hex()])
        assert response["error"]["message"] == f"Empty Neon transaction receipt for {blockhash}"

    # GETH: NDEV-3252
    def test_debug_get_raw_transaction_non_existent_tx_hash(self):
        block_hash = "0xd9765b77e470204ae5edb1a796ab92ecb0e20fea50aeb09275aea740af7bbc69"
        response = self.tracer_api.debug_get_raw_transaction(block_hash)
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32603, "Invalid error code"
        assert (
            response["error"]["message"]
            == "Empty Neon transaction receipt for 0xd9765b77e470204ae5edb1a796ab92ecb0e20fea50aeb09275aea740af7bbc69"
        )

    def test_trace_transaction_from_precompiled_contract(self, precompile_contract_call_tx_receipt):
        tx_hash = precompile_contract_call_tx_receipt["transactionHash"].hex()
        tx_data = self.web3_client.get_transaction_by_hash(tx_hash)

        response = self.tracer_api.debug_trace_call(tx_data)
        assert self.tracer_validator.check_tracer_struct_log(response)

        resp = self.tracer_api.debug_trace_transaction(tx_hash, tracer_type="callTracer", with_log=True)
        assert self.tracer_validator.check_call_tracer_type(resp, tx_data)
