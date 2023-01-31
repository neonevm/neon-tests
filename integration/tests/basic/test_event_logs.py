import random
import string

import pytest
import web3
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature

from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.rpc_checks import assert_log_field_in_neon_trx_receipt
from integration.tests.basic.test_rpc_calls import get_event_signatures
from utils.helpers import wait_condition


class TestLogs(BaseMixin):

    def make_tx_object(self, from_address, gasPrice=None, gas=None, value=None):
        tx = {"from": from_address, "nonce": self.web3_client.eth.get_transaction_count(from_address),
              "gasPrice": gasPrice if gasPrice is not None else self.web3_client.gas_price()}
        if gas is not None:
            tx["gas"] = gas
        type(value)
        if value is not None:
            tx["value"] = web3.Web3.toWei(value, "ether")
        return tx

    def test_non_args_event(self, event_caller):
        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.nonArgs().buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 1
        print(resp)
        event_logs = event_caller.events.NonArgs().processReceipt(resp)
        assert len(event_logs) == 1
        assert event_logs[0].args == {}
        assert event_logs[0].event == "NonArgs"

    def test_all_types_args_event(self, event_caller):
        tx = self.make_tx_object(self.sender_account.address)
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        text_bytes = bytes(text, 'utf-8')
        bol = True
        instruction_tx = event_caller.functions.allTypes(self.sender_account.address, number, text, text_bytes,
                                                         bol).buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 1
        event_logs = event_caller.events.AllTypes().processReceipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 5
        assert event_logs[0].args.addr == self.sender_account.address
        assert event_logs[0].args.u == number
        assert event_logs[0].args.s == text
        assert event_logs[0].args.b == text_bytes + bytes(32 - len(text_bytes))
        assert event_logs[0].args.bol == bol
        assert event_logs[0].event == "AllTypes"

        response = self.proxy_api.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        print(response)
        assert_log_field_in_neon_trx_receipt(response, 1)

        topics = get_event_signatures(event_caller.abi)
        print(topics)


    def test_indexed_args_event(self, event_caller):
        amount = random.randint(1, 100)
        tx = self.make_tx_object(self.sender_account.address, value=amount)
        instruction_tx = event_caller.functions.indexedArgs().buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 3
        event_logs = event_caller.events.IndexedArgs().processReceipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 2
        assert event_logs[0].args.who == self.sender_account.address
        assert event_logs[0].args.value == web3.Web3.toWei(amount, "ether")
        assert event_logs[0].event == "IndexedArgs"

        response = self.proxy_api.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_non_indexed_args_event(self, event_caller):
        amount = random.randint(1, 100)
        tx = self.make_tx_object(self.sender_account.address, value=amount)
        instruction_tx = event_caller.functions.nonIndexedArg("world").buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 1
        event_logs = event_caller.events.NonIndexedArg().processReceipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 1
        assert event_logs[0].args.hello == "world"
        assert event_logs[0].event == "NonIndexedArg"
        response = self.proxy_api.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_unnamed_args_event(self, event_caller):
        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.unnamedArg("hello").buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 1
        event_logs = event_caller.events.UnnamedArg().processReceipt(resp)
        print(event_logs)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 1
        assert event_logs[0].event == "UnnamedArg"
        response = self.proxy_api.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_big_args_count(self, event_caller):
        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.bigArgsCount("hello").buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert len(resp.logs[0].topics) == 4
        event_logs = event_caller.events.BigArgsCount().processReceipt(resp)
        assert len(event_logs) == 1
        assert len(event_logs[0].args) == 10
        assert event_logs[0].event == "BigArgsCount"

        response = self.proxy_api.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 1)

    def test_several_events_in_one_trx(self, event_caller):
        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.emitThreeEvents().buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        event1_logs = event_caller.events.IndexedArgs().processReceipt(resp)
        event2_logs = event_caller.events.NonIndexedArg().processReceipt(resp)
        event3_logs = event_caller.events.AllTypes().processReceipt(resp)
        assert event1_logs[0].event == "IndexedArgs"
        assert event2_logs[0].event == "NonIndexedArg"
        assert event3_logs[0].event == "AllTypes"

        response = self.proxy_api.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, 3)

    @pytest.mark.parametrize("changes_count, expected_trx_status", [(20, 1), (50, 0)])
    def test_many_the_same_events_in_one_trx(self, event_caller, changes_count, expected_trx_status):
        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.updateStorageMap(changes_count).buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert resp['status'] == expected_trx_status
        event_logs = event_caller.events.NonIndexedArg().processReceipt(resp)
        assert len(event_logs) == changes_count
        for log in event_logs:
            assert log.event == "NonIndexedArg"
        response = self.proxy_api.send_rpc(method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()])
        assert_log_field_in_neon_trx_receipt(response, changes_count)

    def test_nested_calls_with_revert(self):

        contract_a, _ = self.web3_client.deploy_and_get_contract("NestedCallsChecker", "0.8.12", self.sender_account,
                                                                 contract_name="A")
        contract_b, _ = self.web3_client.deploy_and_get_contract("NestedCallsChecker", "0.8.12", self.sender_account,
                                                                 contract_name="B")
        contract_c, _ = self.web3_client.deploy_and_get_contract("NestedCallsChecker", "0.8.12", self.sender_account,
                                                                 contract_name="C")
        print(contract_a.address)
        print(contract_b.address)
        print(contract_c.address)

        tx = self.make_tx_object(self.sender_account.address)

        instruction_tx = contract_a.functions.method1(contract_b.address, contract_c.address).buildTransaction(tx)
        resp = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        print(resp)

        # TODO add event checks

