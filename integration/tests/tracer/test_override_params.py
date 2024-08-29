import time
import allure
import pytest
import random

from deepdiff import DeepDiff
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient
from utils.helpers import padhex


# CODE_OVERRIDED is a bytecode of the storage_contract with retrieve() function which returns (number + 1) instead of number
CODE_OVERRIDED = "0x608060405234801561001057600080fd5b506004361061004c5760003560e01c80632e64cec1146100515780635e383d211461006c5780636057361d1461007f578063dce4a44714610094575b600080fd5b6100596100b4565b6040519081526020015b60405180910390f35b61005961007a36600461019b565b6100c8565b61009261008d36600461019b565b6100e9565b005b6100a76100a23660046101b4565b61010d565b60405161006391906101e4565b600080546100c3906001610239565b905090565b600181815481106100d857600080fd5b600091825260209091200154905081565b60008190556040805160208101909152818152610109906001908161013b565b5050565b6060816001600160a01b0316803b806020016040519081016040528181526000908060200190933c92915050565b828054828255906000526020600020908101928215610176579160200282015b8281111561017657825182559160200191906001019061015b565b50610182929150610186565b5090565b5b808211156101825760008155600101610187565b6000602082840312156101ad57600080fd5b5035919050565b6000602082840312156101c657600080fd5b81356001600160a01b03811681146101dd57600080fd5b9392505050565b600060208083528351808285015260005b81811015610211578581018301518582016040015282016101f5565b81811115610223576000604083870101525b50601f01601f1916929092016040019392505050565b6000821982111561025a57634e487b7160e01b600052601160045260246000fd5b50019056fea264697066735822122027ccfc0daba8d2d69d8a56122f60c379952cad9600de2be04409fc7cb4c51c5c64736f6c63430008080033"
    
index_0 = padhex(hex(0), 64)
index_1 = padhex(hex(1), 64)
index_2 = padhex(hex(2), 64)
index_5 = padhex(hex(5), 64)


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug methods with stateOverrides and/or blockOverrides params check")
@pytest.mark.skip(reason="Feature is not implemented yet in tracer/neon-api")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestTracerOverrideParams:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient
    storage_value = random.randint(0, 100)

    @pytest.fixture(scope="class")
    def retrieve_block_tx(self, storage_object):
        receipt = storage_object.retrieve_block(self.accounts[0])
        return self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
    
    @pytest.fixture(scope="class")
    def retrieve_block_timestamp_tx(self, storage_object):
        receipt = storage_object.retrieve_block_timestamp(self.accounts[0])
        return self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

    @pytest.fixture(scope="class")
    def call_storage_tx(self, storage_object):
        _, _, receipt = storage_object.call_storage(self.accounts[0], self.storage_value, "blockNumber")
        return self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

    @pytest.fixture(scope="class")
    def call_store_value_tx(self, storage_object):
        receipt = storage_object.store_value(self.accounts[0], self.storage_value)
        return self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
    
    @pytest.fixture(scope="class")
    def call_sum_of_values_tx(self, storage_object):
        receipt = storage_object.retrieve_sum_of_values(self.accounts[0], self.storage_value, self.storage_value)
        return self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
    
    def retrieve_block_info_tx(self, storage_object):   
        receipt = storage_object.retrieve_block_info(self.accounts[0])
        return self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
    
    def fill_params_for_storage_contract_trace_call(self, tx, is_prestate=False, is_tx_block=False):
        if is_tx_block:
            block_number = hex(tx["blockNumber"])
        else:
            block_number = hex(tx["blockNumber"] - 1)

        params = [
            {
                "to": tx["to"],
                "from": tx["from"],
                "gas": hex(tx["gas"]),
                "gasPrice": hex(tx["gasPrice"]),
                "value": hex(tx["value"]),
                "data": tx["input"].hex(),
            },
            block_number,
        ]

        if is_prestate:
            params.append({"tracer": "prestateTracer"})

        return params

    def test_stateOverrides_debug_traceCall_override_nonce(self, call_storage_tx):
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        address_from = call_storage_tx["from"].lower()
        params[2]["stateOverrides"] = {address_from: {"nonce": 17}}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response_overrided["result"][address_from]["nonce"] != response["result"][address_from]["nonce"]
        assert response_overrided["result"][address_from]["nonce"] == 17

    def test_stateOverrides_debug_traceCall_override_nonce_to_lower_value(self, call_storage_tx):
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)
        nonce = response["result"][call_storage_tx["from"].lower()]["nonce"]

        nonce_overrided = 0
        if nonce - 1 > 0:
            nonce_overrided = nonce - 1

        address_from = call_storage_tx["from"].lower()
        params[2]["stateOverrides"] = {address_from: {"nonce": nonce_overrided}}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response_overrided["result"][address_from]["nonce"] != response["result"][address_from]["nonce"]
        assert response_overrided["result"][address_from]["nonce"] == nonce_overrided

    def test_stateOverrides_debug_traceCall_override_nonce_invalid_param(self, call_storage_tx):
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        address_from = call_storage_tx["from"].lower()
        override_params = {"stateOverrides": {address_from: {"nonce": -1}}, "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    @pytest.mark.parametrize("nonce", [[17, 9], [14, 14], [1, 5], [0, 0]])
    def test_stateOverrides_debug_traceCall_override_nonce_both_accounts(self, call_storage_tx, nonce):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)
        
        params[2]["stateOverrides"] = {address_from: {"nonce": nonce[0]}, address_to: {"nonce": nonce[1]}}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response_overrided["result"][address_to]["nonce"] != response["result"][address_to]["nonce"]
        assert response_overrided["result"][address_to]["nonce"] == nonce[1]
        assert response_overrided["result"][address_from]["nonce"] != response["result"][address_from]["nonce"]
        assert response_overrided["result"][address_from]["nonce"] == nonce[0]

    def test_stateOverrides_debug_traceCall_override_balance_of_contract_account(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params[2]["stateOverrides"] = {address_to: {"balance": "0x1"}}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response_overrided["result"][address_from]["balance"] == response["result"][address_from]["balance"]
        assert response_overrided["result"][address_to]["balance"] != response["result"][address_to]["balance"]
        assert response_overrided["result"][address_to]["balance"] == "0x1"

    def test_stateOverrides_debug_traceCall_override_balance_both_accounts(self, storage_contract):
        sender_account = self.accounts[0]
        tx_raw = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = storage_contract.functions.retrieveSenderBalance().build_transaction(tx_raw)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

        tx = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        address_from = tx["from"].lower()
        address_to = tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(tx)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params_prestate = self.fill_params_for_storage_contract_trace_call(tx, is_prestate=True)
        response_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        override_params = {"stateOverrides": {address_from: {"balance": "0xd8d726b7177a80001"}, 
                                              address_to: {"balance": "0x1aa535d3d0c"}}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        params_prestate[2]["stateOverrides"] = override_params["stateOverrides"]
        response_prestate_overrided = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_prestate_overrided, "Error in response"
        assert response_prestate_overrided["result"][address_from]["balance"] != response_prestate["result"][address_from]["balance"]
        assert response_prestate_overrided["result"][address_from]["balance"] == "0xd8d726b7177a80001"
        assert response_prestate_overrided["result"][address_to]["balance"] != response_prestate["result"][address_to]["balance"]
        assert response_prestate_overrided["result"][address_to]["balance"] == "0x1aa535d3d0c"

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] != response_overrided["result"]["returnValue"]
        assert response_overrided["result"]["returnValue"] == padhex("0xd8d726b7177a80001", 64)[2:]
    
    # NDEV-3009
    def test_stateOverrides_debug_traceCall_override_balance_insufficient_for_tx(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)

        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params[2]["stateOverrides"] = {address_from: {"balance": "0x1aa535d3d0c"}}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32603, "Invalid error code"
        assert response_overrided["error"]["message"] == "neon_api::trace failed"

    def test_stateOverrides_debug_traceCall_override_balance_invalid_format(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"stateOverrides": {address_from: {"balance": "0x25bf6196bd1"}, 
                                              address_to: {"balance": 1700000000000000000}},
                    "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    @pytest.mark.parametrize("code", [[CODE_OVERRIDED, CODE_OVERRIDED], ["0x3485", CODE_OVERRIDED]])
    def test_stateOverrides_debug_traceCall_override_code_of_contract_and_external_accounts(self, call_storage_tx, code):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params_prestate = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        response_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        override_params = {"stateOverrides": {address_from: {"code": code[0]}, 
                                              address_to: {"code": code[1]}}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        params_prestate[2]["stateOverrides"] = override_params["stateOverrides"]
        response_prestate_overrided = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_prestate_overrided, "Error in response"
        assert "code" not in response_prestate["result"][address_from], "Code has not to be in response"
        assert response_prestate_overrided["result"][address_from]["code"] == code[0]
        assert response_prestate_overrided["result"][address_to]["code"] != response_prestate["result"][address_to]["code"]
        assert response_prestate_overrided["result"][address_to]["code"] == code[1]

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == padhex(hex(self.storage_value + 1), 64)[2:]

    def test_stateOverrides_debug_traceCall_override_code_of_contract_account_invalid(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params_prestate = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        response_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        override_params = {"stateOverrides": {address_to: {"code": "0x43"}}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        params_prestate[2]["stateOverrides"] = override_params["stateOverrides"]
        response_prestate_overrided = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_prestate_overrided, "Error in response"
        assert "code" not in response_prestate["result"][address_from], "Code has not to be in response"
        assert "code" not in response_prestate_overrided["result"][address_from], "Code has not to be in response"
        assert response_prestate_overrided["result"][address_to]["code"] != response_prestate["result"][address_to]["code"]
        assert response_prestate_overrided["result"][address_to]["code"] == "0x43"

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == ""

    def test_stateOverrides_debug_traceCall_override_code_of_contract_account(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params_prestate = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        response_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        override_params = {"stateOverrides": {address_to: {"code": CODE_OVERRIDED}}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        params_prestate[2]["stateOverrides"] = override_params["stateOverrides"]
        response_prestate_overrided = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_prestate_overrided, "Error in response"
        assert "code" not in response_prestate["result"][address_from], "Code has not to be in response"
        assert "code" not in response_prestate_overrided["result"][address_from], "Code has not to be in response"
        assert response_prestate_overrided["result"][address_to]["code"] != response_prestate["result"][address_to]["code"]
        assert response_prestate_overrided["result"][address_to]["code"] == CODE_OVERRIDED

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == padhex(hex(self.storage_value + 1), 64)[2:]

    def test_stateOverrides_debug_traceCall_override_code_of_externally_owned_account(self, call_storage_tx):
        address_from = call_storage_tx["from"].lower()
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params_prestate = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        response_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        override_params = {"stateOverrides": {address_from: {"code": "0x92a3"}}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        params_prestate[2]["stateOverrides"] = override_params["stateOverrides"]
        response_prestate_overrided = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_prestate_overrided, "Error in response"
        assert "code" not in response_prestate["result"][address_from], "Code has not to be in response"
        assert response_prestate_overrided["result"][address_from]["code"] == "0x92a3"
        assert response_prestate_overrided["result"][address_to]["code"] == response_prestate["result"][address_to]["code"]

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == response_overrided["result"]["returnValue"]

    @pytest.mark.parametrize("code", ["92a3", "0x92a34"])
    def test_stateOverrides_debug_traceCall_override_code_invalid_format(self, call_storage_tx, code):
        address_from = call_storage_tx["from"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"stateOverrides": {address_from: {"code": code}}, "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    def test_stateOverrides_debug_traceCall_override_state(self, storage_object):
        _, receipt = storage_object.retrieve_doubled_value(self.accounts[0], self.storage_value)
        tx = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        address_to = tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(tx, is_tx_block=True)
        params_prestate = self.fill_params_for_storage_contract_trace_call(tx, is_prestate=True, is_tx_block=True)

        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"code": response_prestate["result"][address_to]["code"], 
                                                             "state": {index_0: padhex(hex(102), 64)}}}
        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_overrided_prestate, "Error in response"
        assert response_prestate["result"][address_to]["storage"][index_0] != \
               response_overrided_prestate["result"][address_to]["storage"][index_0]
        assert response_overrided_prestate["result"][address_to]["storage"][index_0] == padhex(hex(102), 64)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(2*self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == padhex(hex(20), 64)[2:]

    def test_stateOverrides_debug_traceCall_override_state_without_code(self, storage_object):
        _, receipt = storage_object.retrieve_doubled_value(self.accounts[0], self.storage_value)
        tx = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())
        address_to = tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(tx, is_tx_block=True)
        params_prestate = self.fill_params_for_storage_contract_trace_call(tx, is_prestate=True, is_tx_block=True)

        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"state": {index_0: padhex(hex(102), 64)}}}
        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_overrided_prestate, "Error in response"
        assert "storage" not in response_overrided_prestate["result"][address_to]

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(2*self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == ""

    def test_stateOverrides_debug_traceCall_override_state_non_existent_index(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        params_prestate = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        
        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"code": response_prestate["result"][address_to]["code"], 
                                                             "state": {index_5: padhex(hex(self.storage_value + 2), 64)}}}
        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_overrided_prestate, "Error in response"
        assert response_prestate["result"][address_to]["storage"][index_0] == padhex(hex(self.storage_value), 64)
        assert response_overrided_prestate["result"][address_to]["storage"][index_0] == index_0
        assert index_5 not in response_overrided_prestate["result"][address_to]["storage"]

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == index_0[2:]

    def test_stateOverrides_debug_traceCall_override_state_invalid_index(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params[2]["stateOverrides"] = {address_to: {"code": response["result"][address_to]["code"], 
                                                    "state": {"index" : "0x863"}}}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    def test_stateOverrides_debug_traceCall_override_stateDiff_one_index(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        params_prestate = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)

        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"stateDiff": {index_0 : padhex(hex(self.storage_value + 1), 64)}}}
        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_overrided_prestate, "Error in response"
        assert response_overrided_prestate["result"][address_to]["storage"][index_0] == padhex(hex(self.storage_value + 1), 64)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == padhex(hex(self.storage_value + 1), 64)[2:]

    def test_stateOverrides_debug_traceCall_override_stateDiff_two_indexes(self, call_sum_of_values_tx):
        address_to = call_sum_of_values_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_sum_of_values_tx)
        params_prestate = self.fill_params_for_storage_contract_trace_call(call_sum_of_values_tx, is_prestate=True)

        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"stateDiff": {index_0: padhex(hex(101), 64), 
                                                                           index_1: padhex(hex(103), 64)}}}

        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_overrided_prestate, "Error in response"
        assert response_overrided_prestate["result"][address_to]["storage"][index_0] == padhex(hex(101), 64)
        assert response_overrided_prestate["result"][address_to]["storage"][index_1] == padhex(hex(103), 64)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(2*self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == index_5[2:]

    def test_stateOverrides_debug_traceCall_override_stateDiff_add_non_existent_index_and_existed_one(self, call_sum_of_values_tx):
        address_to = call_sum_of_values_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_sum_of_values_tx)
        params_prestate = self.fill_params_for_storage_contract_trace_call(call_sum_of_values_tx, is_prestate=True)

        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"stateDiff": {index_0: padhex(hex(101), 64), 
                                                                           index_5: padhex("0x12", 64)}}}
        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_overrided_prestate, "Error in response"
        assert response_overrided_prestate["result"][address_to]["storage"][index_0] == padhex(hex(101), 64)
        assert response_overrided_prestate["result"][address_to]["storage"][index_1] == response_prestate["result"][address_to]["storage"][index_1]
        assert index_5 not in response_overrided_prestate["result"][address_to]["storage"]

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(2*self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == padhex(hex(self.storage_value), 64)[2:]
    
    def test_stateOverrides_debug_traceCall_override_stateDiff_add_non_existent_index(self, call_store_value_tx):
        address_to = call_store_value_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_store_value_tx)
        params_prestate = self.fill_params_for_storage_contract_trace_call(call_store_value_tx, is_prestate=True)

        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"stateDiff": {index_5: padhex("0x12", 64)}}}
        response_prestate_overrided = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_prestate_overrided, "Error in response"
        assert response_prestate_overrided["result"][address_to]["storage"] == \
            response_prestate_overrided["result"][address_to]["storage"]
        
        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == response_overrided["result"]["returnValue"]

    def test_stateOverrides_debug_traceCall_override_all_params_without_storage(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)

        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params[2]["stateOverrides"] = {address_to: {"code": "0x9029", "nonce": 5, "balance": "0x20"}}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        #code
        assert response_overrided["result"][address_to]["code"] != response["result"][address_to]["code"]
        assert response_overrided["result"][address_to]["code"] == "0x9029"
        #nonce
        assert response_overrided["result"][address_to]["nonce"] != response["result"][address_to]["nonce"]
        assert response_overrided["result"][address_to]["nonce"] == 5
        #balance
        assert response_overrided["result"][address_to]["balance"] != response["result"][address_to]["balance"]
        assert response_overrided["result"][address_to]["balance"] == "0x20"

    def test_stateOverrides_debug_traceCall_override_all_params_with_stateDiff(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        params_prestate = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)

        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"code": CODE_OVERRIDED,  
                                                    "nonce": 5,
                                                    "balance": "0xd8d726b7177a80000",
                                                    "stateDiff": {index_0 : padhex(hex(self.storage_value + 2), 64)}}}

        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_overrided_prestate, "Error in response"
        #code
        assert response_overrided_prestate["result"][address_to]["code"] != response_prestate["result"][address_to]["code"]
        assert response_overrided_prestate["result"][address_to]["code"] == CODE_OVERRIDED
        #nonce
        assert response_overrided_prestate["result"][address_to]["nonce"] != response_prestate["result"][address_to]["nonce"]
        assert response_overrided_prestate["result"][address_to]["nonce"] == 5
        #balance
        assert response_overrided_prestate["result"][address_to]["balance"] != response_prestate["result"][address_to]["balance"]
        assert response_overrided_prestate["result"][address_to]["balance"] == "0xd8d726b7177a80000"
        #storage
        assert response_prestate["result"][address_to]["storage"][index_0] == padhex(hex(self.storage_value), 64)
        assert response_overrided_prestate["result"][address_to]["storage"][index_0] == padhex(hex(self.storage_value + 2), 64)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == padhex(hex(self.storage_value + 3), 64)[2:]

    def test_stateOverrides_debug_traceCall_override_all_params_with_state(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        params_prestate = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)

        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)

        params_prestate[2]["stateOverrides"] = {address_to: {"code": CODE_OVERRIDED,  
                                                    "nonce": 25,
                                                    "state": {index_0 : padhex(hex(self.storage_value + 1), 64)},
                                                    "balance": "0xd8d726b7177a80001"}}

        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params_prestate)

        response = self.tracer_api.send_rpc("debug_traceCall", params)

        override_params = {"stateOverrides": params_prestate[2]["stateOverrides"]}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response_prestate, "Error in response"
        assert "error" not in response_overrided_prestate, "Error in response"
        #code
        assert response_overrided_prestate["result"][address_to]["code"] != response_prestate["result"][address_to]["code"]
        assert response_overrided_prestate["result"][address_to]["code"] == CODE_OVERRIDED
        #nonce
        assert response_overrided_prestate["result"][address_to]["nonce"] != response_prestate["result"][address_to]["nonce"]
        assert response_overrided_prestate["result"][address_to]["nonce"] == 25
        #storage
        assert response_prestate["result"][address_to]["storage"][index_0] == padhex(hex(self.storage_value), 64)
        assert response_overrided_prestate["result"][address_to]["storage"][index_0] == padhex(hex(self.storage_value + 1), 64)
        #balance
        assert response_overrided_prestate["result"][address_to]["balance"] != response_prestate["result"][address_to]["balance"]
        assert response_overrided_prestate["result"][address_to]["balance"] == "0xd8d726b7177a80001"

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert response["result"]["returnValue"] == padhex(hex(self.storage_value), 64)[2:]
        assert response_overrided["result"]["returnValue"] == padhex(hex(self.storage_value + 2), 64)[2:]

    def test_stateOverrides_debug_traceCall_do_not_override_storage(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params[2]["stateOverrides"] = {address_to: {"storage": {index_0: padhex("0x58", 64)}}}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" not in response, "Error in response"
        assert "error" not in response_overrided, "Error in response"
        assert int(response["result"][address_to]["storage"][index_0], 0) == self.storage_value
        assert int(response_overrided["result"][address_to]["storage"][index_0], 0) == self.storage_value

    @pytest.mark.skip("NDEV-3001")
    def test_stateOverrides_debug_traceCall_override_with_state_and_stateDiff(self, call_store_value_tx):
        address_to = call_store_value_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_store_value_tx)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"stateOverrides": {address_to: {"stateDiff": {"0x3" : "0x11"}, "state": {"0x0": "0x15"}}}, 
                           "tracer": "prestateTracer"}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)
        assert "error" in response_overrided, "State and stateDiff are not allowed to be used together"
    
    def test_stateOverrides_debug_traceCall_wrong_override_format(self, call_storage_tx):
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx, is_prestate=True)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        params[2]["stateOverrides"] = {"nonce": 17}
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    @pytest.mark.skip("NDEV-3003")
    def test_stateOverrides_eth_call_override_code(self, call_storage_tx):
        address_to = call_storage_tx["to"].lower()
        params = self.fill_params_for_storage_contract_trace_call(call_storage_tx)
        response = self.tracer_api.send_rpc_and_wait_response("eth_call", params)

        override_params = {address_to: {"code": CODE_OVERRIDED}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("eth_call", params)

        assert response["result"] == padhex(hex(self.storage_value), 64)
        assert response_overrided["result"] == padhex(hex(self.storage_value + 1), 64)

    def test_blockOverrides_debug_traceCall_override_block(self, retrieve_block_tx, call_storage_tx):
        params = self.fill_params_for_storage_contract_trace_call(retrieve_block_tx, is_tx_block=True)
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"blockOverrides": {"number": call_storage_tx["blockNumber"]}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        diff = DeepDiff(response["result"], response_overrided["result"])

        diff_storage = {"new_value": padhex(hex(call_storage_tx["blockNumber"]), 64)[2:], 
                        "old_value": padhex(hex(retrieve_block_tx["blockNumber"]), 64)[2:]}
        diff_block = {"new_value": hex(call_storage_tx["blockNumber"]), 
                      "old_value": hex(retrieve_block_tx["blockNumber"])}
        
        for _,v in diff["values_changed"].items():
            assert v == diff_block or v == diff_storage

    def test_blockOverrides_debug_traceCall_override_block_invalid(self, retrieve_block_tx):
        params = self.fill_params_for_storage_contract_trace_call(retrieve_block_tx, is_tx_block=True)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"blockOverrides": {"number": 0.1}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    # NDEV-3009
    def test_blockOverrides_debug_traceCall_override_block_future(self, retrieve_block_tx):
        params = self.fill_params_for_storage_contract_trace_call(retrieve_block_tx, is_tx_block=True)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        block = self.web3_client.get_block_number()
        override_params = {"blockOverrides": {"number": block + 3}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32603, "Invalid error code"
        assert response_overrided["error"]["message"] == "neon_api::trace failed"

    @pytest.mark.skip("NDEV-3010")
    def test_blockOverrides_debug_traceCall_wrong_override_format(self, retrieve_block_tx, call_storage_tx):
        params = self.fill_params_for_storage_contract_trace_call(retrieve_block_tx, is_tx_block=True)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"blockOverrides": {retrieve_block_tx["to"].lower(): {"number": call_storage_tx["blockNumber"]}}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    def test_blockOverrides_debug_traceCall_override_block_timestamp(self, storage_contract, retrieve_block_timestamp_tx):
        params_prestate = self.fill_params_for_storage_contract_trace_call(retrieve_block_timestamp_tx, 
                                                                           is_prestate=True, 
                                                                           is_tx_block=True)
        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)
        address_to = retrieve_block_timestamp_tx["to"].lower()
        timestamp_new = int(response_prestate["result"][address_to]["storage"][index_0], 0)
        
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = storage_contract.functions.storeBlockTimestamp().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        retrieve_block_timestamp_tx_new = self.web3_client.get_transaction_by_hash(receipt["transactionHash"].hex())

        params_new_prestate = self.fill_params_for_storage_contract_trace_call(retrieve_block_timestamp_tx_new, 
                                                                               is_prestate=True,
                                                                               is_tx_block=True)
        response_new_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_new_prestate)
        address_to = retrieve_block_timestamp_tx_new["to"].lower()
        timestamp = int(response_new_prestate["result"][address_to]["storage"][index_0], 0)

        params = self.fill_params_for_storage_contract_trace_call(retrieve_block_timestamp_tx_new, is_tx_block=True)
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"blockOverrides": {"time": timestamp_new}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        diff = DeepDiff(response["result"], response_overrided["result"])

        diff_storage = {"new_value": padhex(hex(timestamp_new), 64)[2:], 
                        "old_value": padhex(hex(timestamp), 64)[2:]}
        diff_block_timestamp = {"new_value": hex(timestamp_new), "old_value": hex(timestamp)}

        for _,v in diff["values_changed"].items():
            assert v == diff_block_timestamp or v == diff_storage

    def test_blockOverrides_debug_traceCall_override_block_timestamp_invalid_one(self, retrieve_block_timestamp_tx):
        params = self.fill_params_for_storage_contract_trace_call(retrieve_block_timestamp_tx, is_tx_block=True)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"blockOverrides": {"time": "1715360635"}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    def test_blockOverrides_debug_traceCall_override_block_timestamp_to_timestamp_now(self, retrieve_block_timestamp_tx):
        params_prestate = self.fill_params_for_storage_contract_trace_call(retrieve_block_timestamp_tx, 
                                                                           is_prestate=True, 
                                                                           is_tx_block=True)
        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_prestate)
        address_to = retrieve_block_timestamp_tx["to"].lower()
        timestamp = int(response_prestate["result"][address_to]["storage"][index_0], 0)

        params = self.fill_params_for_storage_contract_trace_call(retrieve_block_timestamp_tx, is_tx_block=True)
        response = self.tracer_api.send_rpc("debug_traceCall", params)

        timestamp_new = int(time.time())
        override_params = {"blockOverrides": {"time": timestamp_new}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        diff = DeepDiff(response["result"], response_overrided["result"])

        diff_storage = {"new_value": padhex(hex(timestamp_new), 64)[2:], 
                        "old_value": padhex(hex(timestamp), 64)[2:]}
        diff_block_timestamp = {"new_value": hex(timestamp_new), "old_value": hex(timestamp)}

        for _,v in diff["values_changed"].items():
            assert v == diff_block_timestamp or v == diff_storage

    def test_blockOverrides_debug_traceCall_override_block_number_and_timestamp(self, storage_object):
        block_info_tx_1 = self.retrieve_block_info_tx(storage_object)
        params_1_prestate = self.fill_params_for_storage_contract_trace_call(block_info_tx_1, 
                                                                             is_prestate=True, 
                                                                             is_tx_block=True)
        response_prestate = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_1_prestate)

        address_to_1 = block_info_tx_1["to"].lower()
        timestamp_1 = int(response_prestate["result"][address_to_1]["storage"][index_2], 0)

        params = self.fill_params_for_storage_contract_trace_call(block_info_tx_1, is_tx_block=True)
        response = self.tracer_api.send_rpc("debug_traceCall", params)

        block_info_tx_2 = self.retrieve_block_info_tx(storage_object)
        params_2_prestate = self.fill_params_for_storage_contract_trace_call(block_info_tx_2, 
                                                                             is_prestate=True, 
                                                                             is_tx_block=True)
        response_prestate_2 = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params_2_prestate)
        address_to_2 = block_info_tx_2["to"].lower()
        timestamp_2 = int(response_prestate_2["result"][address_to_2]["storage"][index_2], 0)

        override_params = {"blockOverrides": {"number": block_info_tx_2["blockNumber"], "time": timestamp_2}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        diff = DeepDiff(response["result"], response_overrided["result"])

        diff_storage_block = {"new_value": padhex(hex(block_info_tx_2["blockNumber"]), 64)[2:], 
                        "old_value": padhex(hex(block_info_tx_1["blockNumber"]), 64)[2:]}
        diff_block = {"new_value": hex(block_info_tx_2["blockNumber"]), 
                      "old_value": hex(block_info_tx_1["blockNumber"])}

        diff_storage_time = {"new_value": padhex(hex(timestamp_2), 64)[2:], 
                        "old_value": padhex(hex(timestamp_1), 64)[2:]}
        diff_time = {"new_value": hex(timestamp_2), 
                      "old_value": hex(timestamp_1)}
        
        for _,v in diff["values_changed"].items():
            assert v == diff_block or v == diff_storage_block or v == diff_time or v == diff_storage_time

    def test_blockOverrides_debug_traceCall_override_block_number_and_invalid_timestamp(self, storage_object):
        block_info_tx = self.retrieve_block_info_tx(storage_object)
        params = self.fill_params_for_storage_contract_trace_call(block_info_tx, is_tx_block=True)
        self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        block_info_tx_override = self.retrieve_block_info_tx(storage_object)
        override_params = {"blockOverrides": {"number": block_info_tx_override["blockNumber"], "time": "1715360635"}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        assert "error" in response_overrided, "No errors in response"
        assert response_overrided["error"]["code"] == -32602, "Invalid error code"
        assert response_overrided["error"]["message"] == "Invalid params"

    def test_blockOverrides_and_stateOverrides_debug_traceCall(self, call_storage_tx, retrieve_block_tx):
        address_from = retrieve_block_tx["from"].lower()
        params = self.fill_params_for_storage_contract_trace_call(retrieve_block_tx, is_tx_block=True)
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceCall", params)

        override_params = {"blockOverrides": {"number": call_storage_tx["blockNumber"]}, 
                           "stateOverrides": {address_from: {"nonce": 12, "balance": "0xd8d726b7177a80000"}}}
        params.append(override_params)
        response_overrided = self.tracer_api.send_rpc("debug_traceCall", params)

        params[2]["tracer"] = "prestateTracer"
        response_overrided_prestate = self.tracer_api.send_rpc("debug_traceCall", params)

        diff = DeepDiff(response["result"], response_overrided["result"])

        diff_storage = {"new_value": padhex(hex(call_storage_tx["blockNumber"]), 64)[2:], 
                        "old_value": padhex(hex(retrieve_block_tx["blockNumber"]), 64)[2:]}
        diff_block = {"new_value": hex(call_storage_tx["blockNumber"]), 
                      "old_value": hex(retrieve_block_tx["blockNumber"])}
        
        for _,v in diff["values_changed"].items():
            assert v == diff_block or v == diff_storage
        
        assert "error" not in response_overrided_prestate, "Error in response"
        assert response_overrided_prestate["result"][address_from]["nonce"] == 12
        assert response_overrided_prestate["result"][address_from]["balance"] == "0xd8d726b7177a80000"