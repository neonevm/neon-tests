import random
import string
from collections import Counter

import pytest

import allure
from integration.tests.basic.helpers.basic import NeonEventType
from integration.tests.basic.helpers.rpc_checks import (
    assert_events_by_type,
    assert_event_field,
    assert_events_order,
    count_events,
)
from utils.accounts import EthAccounts
from utils.models.result import NeonGetTransactionResult
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify events")
@pytest.mark.usefixtures("accounts", "web3_client")
@pytest.mark.neon_only
class TestEvents:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_events_for_trx_with_transfer(self, json_rpc_client):
        sender_account, receiver_account = self.accounts[0], self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account, receiver_account, 1000, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert count_events(validated_response) == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1})
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_field_values_for_trx_with_transfer(self, json_rpc_client):
        sender_account, receiver_account = self.accounts[0], self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account, receiver_account, 1000, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        transaction_hash = resp["transactionHash"].hex()
        assert_event_field(validated_response, NeonEventType.EnterCall, "transactionHash", transaction_hash)
        assert_event_field(validated_response, NeonEventType.ExitStop, "transactionHash", transaction_hash)
        assert_event_field(validated_response, NeonEventType.Return, "transactionHash", transaction_hash)

        assert_event_field(validated_response, NeonEventType.EnterCall, "address", receiver_account.address)
        assert_event_field(validated_response, NeonEventType.ExitStop, "address", receiver_account.address)
        assert_event_field(validated_response, NeonEventType.Return, "address", None)

        assert count_events(validated_response) == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1})
        assert_events_by_type(validated_response)

    def test_events_for_trx_with_logs(self, json_rpc_client, event_caller_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        number = random.randint(1, 5)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b"\0")

        instruction_tx = event_caller_contract.functions.allTypes(
            sender_account.address, number, text, bytes_array, True
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert count_events(validated_response) == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1, "Log": 1})

        assert_event_field(validated_response, NeonEventType.EnterCall, "address", validated_response.result.to)
        assert_event_field(validated_response, NeonEventType.ExitStop, "address", validated_response.result.to)
        assert_event_field(validated_response, NeonEventType.Log, "address", validated_response.result.to)
        assert_event_field(validated_response, NeonEventType.Return, "address", None)

        assert_events_by_type(validated_response)

    def test_events_for_trx_with_nested_call(self, json_rpc_client, nested_call_contracts):
        sender_account = self.accounts[0]
        contract_a, contract_b, contract_c = nested_call_contracts
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_a.functions.method1(contract_b.address, contract_c.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert count_events(validated_response) == Counter({"EnterCall": 4, "ExitStop": 2, "Return": 1, "Log": 2})
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_contract_iterative_tx(self, counter_contract, json_rpc_client):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)

        instruction_tx = counter_contract.functions.moreInstructionWithLogs(0, 1000).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert len(validated_response.result.solanaTransactions) > 1
        assert count_events(validated_response) == Counter({"EnterCall": 1, "ExitStop": 1, "Return": 1, "Log": 1001})
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_event_enter_call_code(self, json_rpc_client, opcodes_checker):
        # Will be depricated in the future https://eips.ethereum.org/EIPS/eip-2488
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = opcodes_checker.functions.test_callcode().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert count_events(validated_response) == Counter(
            {"EnterCall": 1, "ExitStop": 1, "Return": 1, "EnterCallCode": 1, "ExitReturn": 1}
        )
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_event_enter_static_call(self, json_rpc_client, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.emitEventAndGetBalanceOfContractCalleeWithEvents(
            event_checker_callee_address
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.send_rpc(
            method="neon_getTransactionReceipt", params=[receipt["transactionHash"].hex()]
        )
        validated_response = NeonGetTransactionResult(**response)
        assert count_events(validated_response) == Counter(
            {"EnterCall": 2, "ExitStop": 1, "Return": 1, "Log": 2, "EnterStaticCall": 1, "ExitReturn": 2}
        )
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_event_enter_delegate_call(self, json_rpc_client, events_checker_contract, event_checker_callee_address):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = events_checker_contract.functions.setParamWithDelegateCall(
            event_checker_callee_address, 9
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)
        assert count_events(validated_response) == Counter(
            {"EnterCall": 1, "ExitStop": 2, "Return": 1, "EnterDelegateCall": 1}
        )
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)
        assert_event_field(
            validated_response, NeonEventType.EnterDelegateCall, "address", validated_response.result.to, "!="
        )

    def test_event_enter_create_2(self, json_rpc_client, events_checker_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = events_checker_contract.functions.callTypeCreate2().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)
        assert_events_order(validated_response)
        # There is no EnterCreate2 event for now. Expecting EnterCreate.
        assert count_events(validated_response) == Counter(
            {"EnterCall": 1, "Return": 1, "EnterCreate": 1, "ExitReturn": 2}
        )
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_event_exit_return(self, json_rpc_client, opcodes_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = opcodes_checker.functions.test_callcode().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert count_events(validated_response) == Counter(
            {"EnterCall": 1, "ExitStop": 1, "Return": 1, "EnterCallCode": 1, "ExitReturn": 1}
        )
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_event_exit_self_destruct(self, json_rpc_client, destroyable_contract):
        # SELFDESTRUCT by changing it to SENDALL https://eips.ethereum.org/EIPS/eip-4758
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = destroyable_contract.functions.destroy(sender_account.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert count_events(validated_response) == Counter({"EnterCall": 1, "ExitSendAll": 1, "Return": 1})
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_event_exit_send_all(self, json_rpc_client, destroyable_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = destroyable_contract.functions.destroy(sender_account.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert count_events(validated_response) == Counter({"EnterCall": 1, "ExitSendAll": 1, "Return": 1})
        assert_events_order(validated_response)
        assert_events_by_type(validated_response)

    def test_event_cancel(self, json_rpc_client, expected_error_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
        try:
            resp = self.web3_client.send_transaction(sender_account, instruction_tx)
            assert resp["status"] == 0
        except ValueError as exc:
            assert "Error: memory allocation failed, out of memory." in exc.args[0]["message"]
        finally:
            response = json_rpc_client.send_rpc(
                method="neon_getTransactionReceipt", params=[resp["transactionHash"].hex()]
            )
            validated_response = NeonGetTransactionResult(**response)
            assert count_events(validated_response) == Counter({"Cancel": 1})
            assert_events_order(validated_response)
            assert_events_by_type(validated_response)
