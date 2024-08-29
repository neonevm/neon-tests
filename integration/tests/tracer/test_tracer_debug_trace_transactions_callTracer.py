import random
import allure
import pytest

from deepdiff import DeepDiff
from integration.tests.basic.helpers.basic import AccountData
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug method trace_transaction callTracer check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestDebugTraceTransactionCallTracer:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient

    def fill_expected_response(self,
                               instruction_tx, receipt, 
                               type="CALL",
                               logs=False,
                               calls=True, 
                               revert=False, 
                               revert_reason=None,
                               error=None, 
                               calls_value="0x1", 
                               calls_type="CALL", 
                               calls_logs_append=False
                               ):
        expected_response = {}

        address_to = instruction_tx["to"].lower()
        expected_response["from"] = instruction_tx["from"].lower()
        expected_response["to"] = address_to
        expected_response["gasUsed"] =  hex(receipt["gasUsed"])
        expected_response["input"] = instruction_tx["data"]
        expected_response["type"] = type

        # gasUsed, gas are 0x0 because NeonEVM has different(from goEth) gas calculation logic 
        if calls:
            expected_response["calls"] = []
            expected_response["calls"].append({
                "from": address_to,
                "gasUsed":"0x0",
                "gas": "0x0",
                "type": calls_type,
                "value": calls_value,
            })

            if calls_type == "DELEGATECALL":
                expected_response["calls"][0]["from"] = instruction_tx["to"].lower()

            if calls_logs_append:
                for log in receipt["logs"]:
                    if log["logIndex"] == 1:
                        expected_response["calls"].append({
                        "from": address_to,
                        "gasUsed":"0x0",
                        "gas": "0x0",
                        "type": "CALL",
                        "value": calls_value,
                        "logs": [{
                            "topics": [log["topics"][0].hex()],
                            "data": log["data"].hex(),
                            }]
                        })

        if logs:
            for log in receipt["logs"]:
                if log["logIndex"] == 0:
                    expected_response["logs"] = [{
                        "address": address_to,
                        "topics": [log["topics"][0].hex()],
                        "data": log["data"].hex(),
                    }]

        if revert:
            if error:
                expected_response["calls"][0]["error"] = revert_reason
            else:
                expected_response["calls"][0]["error"] = "execution reverted"
                expected_response["calls"][0]["revertReason"] = revert_reason

        return expected_response

    def assert_response_contains_expected(self, pytestconfig, expected_response, response, sort_calls=False):
        if sort_calls:
            expected_response["calls"] = sorted(expected_response["calls"], key=lambda d: d['type'])
            response["result"]["calls"] = sorted(response["result"]["calls"], key=lambda d: d['type'])
        
        if pytestconfig.getoption("--network") == "geth":
            # we do not fill whole response, that is why we skip some of fields
            # we can build compare function for each field in the future if it needed
            exclude_list = ["root['gas']", "root['output']", "root['value']"]
            if "calls" in expected_response:
                for i in range(len(expected_response["calls"])):
                    exclude_list.append(f"root['calls'][{i}]['to']")
                    exclude_list.append(f"root['calls'][{i}]['gas']")
                    exclude_list.append(f"root['calls'][{i}]['gasUsed']")
                    exclude_list.append(f"root['calls'][{i}]['input']")
                    exclude_list.append(f"root['calls'][{i}]['output']")
                    exclude_list.append(f"root['calls'][{i}]['value']")
                    exclude_list.append(f"root['calls'][{i}]['logs'][0]['address']")
                    exclude_list.append(f"root['calls'][{i}]['logs'][0]['position']")
        else:
            exclude_list = []

        diff = DeepDiff(expected_response, response["result"], exclude_paths=exclude_list)
        # check if expected_response is subset of response
        assert "dictionary_item_removed" not in diff
        # check if expected_response and response match in identical keys
        assert "values_changed" not in diff

    def test_callTracer_type_create(self, pytestconfig, storage_contract_with_deploy_tx):
        receipt = storage_contract_with_deploy_tx[1]
        expected_response = {}
        
        tracer_params = { "tracer": "callTracer", "tracerConfig": { "onlyTopCall": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response["from"] = receipt["from"].lower()
        expected_response["to"] = receipt["contractAddress"].lower()
        expected_response["gasUsed"] =  hex(receipt["gasUsed"])
        expected_response["type"] = "CREATE"

        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_type_create2(self, pytestconfig, events_checker_contract):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.callTypeCreate2().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, receipt, calls_value="0x0", calls_type="CREATE2")
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_type_call(self, pytestconfig, storage_object):
        sender_account = self.accounts[0]
        store_value = random.randint(1, 100)
    
        tx_obj, _, receipt = storage_object.call_storage(sender_account, store_value, "blockNumber")

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "onlyTopCall": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(tx_obj, receipt, calls=False)
        self.assert_response_contains_expected(pytestconfig, expected_response, response)
    
    def test_callTracer_withLog_check(self, pytestconfig, event_caller_contract):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = event_caller_contract.functions.callEvent1("Event call").build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, receipt, calls=False, logs=True)
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": False } }
        response = self.tracer_api.send_rpc(
            method="debug_traceTransaction", params=[receipt["transactionHash"].hex(), tracer_params]
        )
        assert "logs" not in response["result"]
    
    @pytest.mark.skip(reason="NDEV-2959")
    def test_callTracer_onlyTopCall_check(self, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.emitEventAndGetValueContractCalleeWithEventsAndSubcall(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "OnlyTopCall": False } }
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", 
                                                              [receipt["transactionHash"].hex(), tracer_params])

        assert len(response["result"]["calls"]) == 2
        assert len(response["result"]["calls"][1]["calls"]) == 2
        assert response["result"]["calls"][1]["calls"][0]["type"] == "CREATE"
        assert response["result"]["calls"][1]["calls"][1]["type"] == "STATICCALL"

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "OnlyTopCall": True } }
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", 
                                                              [receipt["transactionHash"].hex(), tracer_params])
        assert "calls" not in response["result"]

    def test_callTracer_call_contract_from_contract_type_static_call(self, 
                                                                     pytestconfig, 
                                                                     events_checker_contract, 
                                                                     event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.getBalanceOfContractCallee(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "OnlyTopCall": False } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, receipt, calls_value="0x0", calls_type="STATICCALL")
        self.assert_response_contains_expected(pytestconfig, expected_response, response)
   
    def test_callTracer_call_contract_from_contract_type_static_call_with_events(self, 
                                                                                 pytestconfig, 
                                                                                 events_checker_contract, 
                                                                                 event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.emitEventAndGetBalanceOfContractCalleeWithEvents(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, 
                                                        receipt, 
                                                        logs=True, 
                                                        calls_value="0x0", 
                                                        calls_type="STATICCALL", 
                                                        calls_logs_append=True)
        self.assert_response_contains_expected(pytestconfig, expected_response, response, sort_calls=True)
    
    def test_callTracer_call_contract_from_contract_type_call_with_events(self, 
                                                                          pytestconfig, 
                                                                          events_checker_contract, 
                                                                          event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.lowLevelCallContractWithEvents(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, 
                                                receipt, 
                                                logs=True, 
                                                calls_value="0x0",
                                                calls_logs_append=True)
        self.assert_response_contains_expected(pytestconfig, expected_response, response, sort_calls=True)

    def test_callTracer_call_contract_from_contract_type_call(self, pytestconfig, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.lowLevelCallContract(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, receipt, calls_value="0x0")
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    @pytest.mark.skip(reason="SLA-119")
    def test_callTracer_call_contract_from_contract_type_delegate_call(self, pytestconfig, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.setParamWithDelegateCall(
            event_checker_callee_address, 9).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": False } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, receipt, calls_value="0x0", calls_type="DELEGATECALL")
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_from_contract_type_callcode(self, pytestconfig, opcodes_checker):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = opcodes_checker.functions.test_callcode().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        
        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, receipt, calls_value="0x0", calls_type="CALLCODE")
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_with_zero_division(self, pytestconfig, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.callNotSafeDivision(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, 
                                                        receipt, 
                                                        revert=True, 
                                                        revert_reason="division or modulo by zero", 
                                                        calls_value="0x0")

        self.assert_response_contains_expected(pytestconfig, expected_response, response)
    
    def test_callTracer_call_contract_from_other_contract_revert_with_assert(self, pytestconfig, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.callContactRevertWithAssertFalse(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, 
                                                        receipt, 
                                                        logs=True, 
                                                        revert=True, 
                                                        revert_reason="assert(false)", 
                                                        calls_value="0x0")

        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_from_other_contract_trivial_revert(self, pytestconfig, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.callContactTrivialRevert(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, 
                                                        receipt, 
                                                        logs=True, 
                                                        revert=True, 
                                                        revert_reason="Revert Contract",
                                                        calls_value="0x0")
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    @pytest.mark.skip(reason="NDEV-3260")
    def test_callTracer_call_contract_from_other_contract_revert(self, pytestconfig, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.callContactRevertInsufficientBalance(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        address_to = instruction_tx["to"].lower()
        if pytestconfig.getoption("--network") == "geth":
            reason = "insufficient balance for transfer"
        else:
            reason = f"Insufficient balance for transfer, account = {address_to}, chain = {self.web3_client.eth.chain_id}, required = 1"
        expected_response = self.fill_expected_response(instruction_tx, receipt, logs=True, revert=True, error=reason)
        self.assert_response_contains_expected(pytestconfig, expected_response, response)
    
    def test_callTracer_call_contract_from_other_contract_revert_with_require(self, pytestconfig, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.callContractRevertWithRequire(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, 
                                                        receipt, 
                                                        logs=True, 
                                                        revert=True, 
                                                        revert_reason="require False", 
                                                        calls_value="0x0")
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_to_precompiled_contract(self, pytestconfig, eip1052_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        precompiled_acc = AccountData(address="0xFf00000000000000000000000000000000000004")

        instruction_tx = eip1052_checker.functions.getContractHashWithLog(precompiled_acc.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        
        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": False } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(instruction_tx, receipt, calls=False)
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    @pytest.mark.skip(reason="NDEV-2934")
    def test_callTracer_without_tracerConfig(self, pytestconfig, storage_object):
        sender_account = self.accounts[0]
        store_value = random.randint(1, 100)
    
        tx_obj, _, receipt = storage_object.call_storage(sender_account, store_value, "blockNumber")

        tracer_params = { "tracer": "callTracer" }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        expected_response = self.fill_expected_response(tx_obj, receipt, calls=False)
        self.assert_response_contains_expected(pytestconfig, expected_response, response)

    def test_callTracer_call_contract_with_event_from_other_one_with_two_events(self, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.emitAllEventsAndCallContractCalleeWithEvent(
            event_checker_callee_address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        #check if all topics from receipt logs are in response logs
        log_topics = []
        for log in receipt["logs"]:
            log_topics.append(log["topics"][0].hex())
        
        for topic in log_topics:
            assert topic in response["result"]["logs"][0]["topics"] \
                or topic in response["result"]["logs"][1]["topics"] \
                or topic in response["result"]["calls"][0]["logs"][0]["topics"]

    def test_callTracer_new_contract_and_event_from_constructor(self, events_checker_contract):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.callChildWithEventAndContractCreationInConstructor().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        tracer_params = { "tracer": "callTracer", "tracerConfig": { "withLog": True } }
        params = [receipt["transactionHash"].hex(), tracer_params]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)

        assert len(response["result"]["calls"]) == 1
        assert len(response["result"]["calls"][0]["calls"]) == 1
        assert len(response["result"]["calls"][0]["logs"]) == 1
        assert response["result"]["type"] == "CALL"
        assert response["result"]["calls"][0]["type"] == "CREATE"
        assert response["result"]["calls"][0]["calls"][0]["type"] == "CREATE"
        assert response["result"]["calls"][0]["logs"][0]["topics"][0] == receipt["logs"][0]["topics"][0].hex()
