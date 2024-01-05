import random
import string

import pytest
import allure
import web3
from web3.logs import DISCARD

from integration.tests.basic.helpers.rpc_checks import (
    assert_log_field_in_neon_trx_receipt,
)
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts


@allure.feature("JSON-RPC validation")
@allure.story("Verify events and logs")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestLogs:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_non_args_event(self, event_caller_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = event_caller_contract.functions.nonArgs().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 1
        event_logs = event_caller_contract.events.NonArgs().process_receipt(resp)
        assert len(event_logs) == 1
        assert event_logs[0].args == {}
        assert event_logs[0].event == "NonArgs"

    def test_all_types_args_event(self, event_caller_contract, json_rpc_client):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b"\0")
        bol = True

        instruction_tx = event_caller_contract.functions.allTypes(
            sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 1
        event_logs = event_caller_contract.events.AllTypes().process_receipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 5
        assert event_logs[0].args.addr == sender_account.address
        assert event_logs[0].args.u == number
        assert event_logs[0].args.s == text
        assert event_logs[0].args.b == bytes_array
        assert event_logs[0].args.bol == bol
        assert event_logs[0].event == "AllTypes"
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_indexed_args_event(self, event_caller_contract, json_rpc_client):
        amount = random.randint(1, 100)
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, amount=amount)
        instruction_tx = event_caller_contract.functions.indexedArgs().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 3
        event_logs = event_caller_contract.events.IndexedArgs().process_receipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 2
        assert event_logs[0].args.who == sender_account.address
        assert event_logs[0].args.value == amount
        assert event_logs[0].event == "IndexedArgs"

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_non_indexed_args_event(self, event_caller_contract, json_rpc_client):
        amount = random.randint(1, 100)
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, amount=amount)
        instruction_tx = event_caller_contract.functions.nonIndexedArg("world").build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 1
        event_logs = event_caller_contract.events.NonIndexedArg().process_receipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 1
        assert event_logs[0].args.hello == "world"
        assert event_logs[0].event == "NonIndexedArg"
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_unnamed_args_event(self, event_caller_contract, json_rpc_client):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = event_caller_contract.functions.unnamedArg("hello").build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 1
        event_logs = event_caller_contract.events.UnnamedArg().process_receipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 1
        assert event_logs[0].event == "UnnamedArg"
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_big_args_count(self, event_caller_contract, json_rpc_client):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = event_caller_contract.functions.bigArgsCount("hello").build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 4
        event_logs = event_caller_contract.events.BigArgsCount().process_receipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 10
        assert event_logs[0].event == "BigArgsCount"

        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_several_events_in_one_trx(self, event_caller_contract, json_rpc_client):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = event_caller_contract.functions.emitThreeEvents().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        event1_logs = event_caller_contract.events.IndexedArgs().process_receipt(resp, errors=DISCARD)
        event2_logs = event_caller_contract.events.NonIndexedArg().process_receipt(resp, errors=DISCARD)
        event3_logs = event_caller_contract.events.AllTypes().process_receipt(resp, errors=DISCARD)
        assert event1_logs[0].event == "IndexedArgs"
        assert event2_logs[0].event == "NonIndexedArg"
        assert event3_logs[0].event == "AllTypes"
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 3)

    def test_many_the_same_events_in_one_trx(self, event_caller_contract, json_rpc_client):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, gas=0)
        changes_count = 20
        instruction_tx = event_caller_contract.functions.updateStorageMap(changes_count).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1
        event_logs = event_caller_contract.events.NonIndexedArg().process_receipt(resp)
        assert len(event_logs) == changes_count
        for log in event_logs:
            assert log.event == "NonIndexedArg"
        response = json_rpc_client.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, changes_count)

    def test_event_logs_deleted_if_trx_was_canceled(self, event_caller_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = event_caller_contract.functions.causeOutOfMemory().build_transaction(tx)
        try:
            resp = self.web3_client.send_transaction(sender_account, instruction_tx)
            assert resp["status"] == 0
            event_logs = event_caller_contract.events.NonIndexedArg().process_receipt(resp)
            assert len(event_logs) == 0
        except ValueError as exc:
            assert "Error: memory allocation failed, out of memory." in exc.args[0]["message"]

    def test_nested_calls_with_revert(self):
        sender_account = self.accounts[0]
        contract_a, _ = self.web3_client.deploy_and_get_contract(
            "common/NestedCallsChecker", "0.8.12", sender_account, contract_name="A"
        )
        contract_b, _ = self.web3_client.deploy_and_get_contract(
            "common/NestedCallsChecker", "0.8.12", sender_account, contract_name="B"
        )
        contract_c, _ = self.web3_client.deploy_and_get_contract(
            "common/NestedCallsChecker", "0.8.12", sender_account, contract_name="C"
        )
        tx = self.web3_client.make_raw_tx(sender_account)

        instruction_tx = contract_a.functions.method1(contract_b.address, contract_c.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_a1_logs = contract_a.events.EventA1().process_receipt(resp, errors=DISCARD)
        assert len(event_a1_logs) == 1
        event_b1_logs = contract_b.events.EventB1().process_receipt(resp, errors=DISCARD)
        assert len(event_b1_logs) == 1
        event_b2_logs = contract_b.events.EventB2().process_receipt(resp, errors=DISCARD)
        event_c1_logs = contract_c.events.EventC1().process_receipt(resp, errors=DISCARD)
        event_c2_logs = contract_c.events.EventC2().process_receipt(resp, errors=DISCARD)
        for log in (event_b2_logs, event_c1_logs, event_c2_logs):
            assert log == (), f"Trx shouldn't contain logs for the events: eventB2, eventC1, eventC2_log0. Log: {log}"
