import random
import string
from enum import Enum

import allure
import pytest
from web3.types import TxParams

from integration.tests.basic.helpers.basic import BaseMixin, Tag
from integration.tests.basic.helpers.errors import Error32602, Error32600
from integration.tests.basic.helpers.rpc_checks import (
    assert_fields_are_hex,
    assert_fields_are_specified_type,
    assert_equal_fields,
)
from integration.tests.helpers.basic import cryptohex


class Method(Enum):
    ETH_GET_LOGS = "eth_getLogs"
    NEON_GET_LOGS = "neon_getLogs"


@allure.feature("JSON-RPC validation")
@allure.story("Verify getLogs method")
class TestRpcGetLogs(BaseMixin):
    ETH_HEX_FIELDS = [
        "transactionHash",
        "blockHash",
        "blockNumber",
        "transactionIndex",
        "address",
        "logIndex",
        "data",
        "transactionLogIndex",
    ]
    ETH_BOOL_FIELDS = ["removed"]
    NEON_HASH_FIELDS = ["neonSolHash"]
    NEON_INT_FIELDS = [
        "neonIxIdx",
        "neonInnerIxIdx",
        "neonEventLevel",
        "neonEventOrder",
    ]

    def create_all_types_instruction(self, event_caller_contract) -> TxParams:
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b"\0")
        bol = True
        tx = self.make_contract_tx_object()
        instruction_tx = event_caller_contract.functions.allTypes(
            self.sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)

        return instruction_tx

    @pytest.mark.parametrize("method", [Method.NEON_GET_LOGS, Method.ETH_GET_LOGS])
    @pytest.mark.parametrize("param_fields", [("address", "topics"), ("address",), ("topics",)])
    def test_get_logs_blockhash(self, method, event_caller_contract, param_fields):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"blockHash": receipt["blockHash"].hex()}

        topic = False
        if "address" in param_fields:
            params["address"] = event_caller_contract.address
        if "topics" in param_fields:
            topic = cryptohex("AllTypes(address,uint256,string,bytes32,bool)")
            params["topics"] = [topic]

        response = self.proxy_api.send_rpc(method.value, params=params)
        assert "error" not in response
        result = response["result"][0]
        if topic:
            assert topic in result["topics"]

        assert_fields_are_hex(result, self.ETH_HEX_FIELDS)
        assert_fields_are_specified_type(bool, result, self.ETH_BOOL_FIELDS)
        if method is Method.NEON_GET_LOGS:
            assert_fields_are_specified_type(int, result, self.NEON_INT_FIELDS)
            assert_fields_are_specified_type(str, result, self.NEON_HASH_FIELDS)

    @pytest.mark.parametrize("method", [Method.NEON_GET_LOGS, Method.ETH_GET_LOGS])
    def test_get_logs_blockhash_empty_params(self, method, event_caller_contract):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        params = {"blockHash": receipt["blockHash"].hex()}
        response = self.proxy_api.send_rpc(method.value, params=params)

        assert "error" not in response
        result = response["result"][0]
        assert_fields_are_hex(result, self.ETH_HEX_FIELDS)
        assert_fields_are_specified_type(bool, result, self.ETH_BOOL_FIELDS)
        assert_equal_fields(result, receipt["logs"][0], ["blockHash"])
        if method is Method.NEON_GET_LOGS:
            assert_fields_are_specified_type(int, result, self.NEON_INT_FIELDS)
            assert_fields_are_specified_type(str, result, self.NEON_HASH_FIELDS)

    @pytest.mark.parametrize("method", [Method.NEON_GET_LOGS, Method.ETH_GET_LOGS])
    @pytest.mark.parametrize(
        "tag1, tag2",
        [
            (Tag.EARLIEST, None),
            (None, Tag.LATEST),
        ],
    )
    def test_get_logs_blockhash_negative_tags(self, method, event_caller_contract, tag1, tag2):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"blockHash": receipt["blockHash"].hex()}
        if tag1:
            params["fromBlock"] = tag1.value
        if tag2:
            params["toBlock"] = tag2.value

        response = self.proxy_api.send_rpc(method.value, params=params)
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]
        assert Error32600.CODE == response["error"]["code"]
        assert Error32600.INVALID_FILTER in response["error"]["message"]

    @pytest.mark.parametrize("method", [Method.NEON_GET_LOGS, Method.ETH_GET_LOGS])
    @pytest.mark.parametrize(
        ("p_name", "p_value", "p_error", "p_code"),
        [
            ("address", "0xc0ffee254729296a45a3885639AC7E10F9d54979", None, None),
            ("address", "12345", Error32602.BAD_ADDRESS, Error32602.CODE),
            ("topics", "Invalid(address,uint256,string,bytes32,bool)", Error32602.BAD_TOPIC, Error32602.CODE),
        ],
    )
    def test_get_logs_negative_params(self, method, event_caller_contract, p_name, p_value, p_error, p_code):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"fromBlock": Tag.EARLIEST.value, "toBlock": Tag.LATEST.value}
        if p_name == "address":
            params["address"] = p_value
        if p_name == "topics":
            params["topics"] = [p_value]

        response = self.proxy_api.send_rpc(method.value, params=params)
        if not p_error and p_name == "address":
            assert "error" not in response
            assert "result" in response
            assert len(response["result"]) == 0, "should not find any logs since the wrong address was provided"
        else:
            assert "error" in response
            assert "code" in response["error"]
            assert "message" in response["error"]
            assert p_code == response["error"]["code"]
            assert p_error in response["error"]["message"]

    @pytest.mark.parametrize("method", [Method.NEON_GET_LOGS, Method.ETH_GET_LOGS])
    @pytest.mark.parametrize(
        "tag1, tag2",
        [
            (-10, 0),
            (0, None),
            (-100, 100),
            (None, None),
            (None, Tag.LATEST),
            (None, Tag.PENDING),
            (None, Tag.EARLIEST),
            (Tag.LATEST, Tag.LATEST),
            (Tag.LATEST, Tag.PENDING),
            (Tag.LATEST, Tag.EARLIEST),
            (Tag.LATEST, None),
            (Tag.PENDING, Tag.PENDING),
            (Tag.PENDING, Tag.LATEST),
            (Tag.PENDING, Tag.EARLIEST),
            (Tag.PENDING, None),
            (Tag.EARLIEST, Tag.EARLIEST),
            (Tag.EARLIEST, Tag.PENDING),
            (Tag.EARLIEST, Tag.LATEST),
            (Tag.EARLIEST, None),
        ],
    )
    @pytest.mark.parametrize("param_fields", [("address", "topics"), ("address",), ("topics",)])
    def test_get_logs(self, method, event_caller_contract, param_fields, tag1, tag2):
        params = {}
        block_number = False
        if isinstance(tag1, int) or isinstance(tag2, int):
            response = self.proxy_api.send_rpc(method="eth_blockNumber")
            assert "result" in response
            block_number = int(response["result"], 16)
        if tag1 or isinstance(tag1, int):
            params["fromBlock"] = hex(block_number + tag1) if isinstance(tag1, int) else tag1.value
        if tag2 or isinstance(tag2, int):
            params["toBlock"] = hex(block_number + tag2) if isinstance(tag2, int) else tag2.value

        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        topic = False
        if "address" in param_fields:
            params["address"] = event_caller_contract.address
        if "topics" in param_fields:
            topic = cryptohex("AllTypes(address,uint256,string,bytes32,bool)")
            params["topics"] = [topic]

        response = self.proxy_api.send_rpc(method.value, params=params)
        assert "error" not in response
        if response["result"]:
            result = response["result"][0]
            if topic:
                assert topic in result["topics"]
            if "address" in param_fields:
                assert response["result"][0]["address"] == receipt["to"], (
                    f"address from response {response['result'][0]['address']} "
                    f"is not equal to address from receipt {receipt['to']}"
                )

            assert_fields_are_hex(result, self.ETH_HEX_FIELDS)
            assert_fields_are_specified_type(bool, result, self.ETH_BOOL_FIELDS)
            if method is Method.NEON_GET_LOGS:
                assert_fields_are_specified_type(int, result, self.NEON_INT_FIELDS)
                assert_fields_are_specified_type(str, result, self.NEON_HASH_FIELDS)

    @pytest.mark.parametrize("method", [Method.NEON_GET_LOGS, Method.ETH_GET_LOGS])
    def test_get_logs_eq_val(self, method, event_caller_contract):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {
            "blockHash": receipt["blockHash"].hex(),
            "address": event_caller_contract.address,
        }
        topic = cryptohex("AllTypes(address,uint256,string,bytes32,bool)")
        params["topics"] = [topic]

        response = self.proxy_api.send_rpc(method.value, params=params)
        assert "error" not in response
        assert "result" in response
        result = response["result"][0]
        assert topic in result["topics"]
        assert_fields_are_hex(result, self.ETH_HEX_FIELDS)
        assert_fields_are_specified_type(bool, result, self.ETH_BOOL_FIELDS)
        if method is Method.NEON_GET_LOGS:
            assert_fields_are_specified_type(int, result, self.NEON_INT_FIELDS)
            assert_fields_are_specified_type(str, result, self.NEON_HASH_FIELDS)

        assert_equal_fields(result, receipt["logs"][0], self.ETH_HEX_FIELDS)

    @pytest.mark.parametrize("method", [Method.NEON_GET_LOGS, Method.ETH_GET_LOGS])
    def test_get_logs_list_of_addresses(self, method, event_caller_contract):
        event_caller2, _ = self.web3_client.deploy_and_get_contract(
            # we need 2nd contract to check list of addresses
            "common/EventCaller",
            "0.8.12",
            self.sender_account,
        )

        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        tx = self.make_contract_tx_object()
        # transaction for first contract
        instruction_tx = event_caller_contract.functions.callEvent1(text).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx2 = self.make_contract_tx_object()
        # transaction for second contract
        instruction_tx2 = event_caller2.functions.callEvent1(text).build_transaction(tx2)
        self.web3_client.send_transaction(self.sender_account, instruction_tx2)

        params = {"address": [event_caller_contract.address, event_caller2.address]}  # list of addresses
        topic = cryptohex("Event1(string)")
        params["topics"] = [topic, cryptohex(text)]

        response = self.proxy_api.send_rpc(method.value, params=params)
        assert "error" not in response
        assert "result" in response
        result = response["result"]
        assert len(result) == 2, f"there should be 2 logs events from 2 contract, but got {len(result)}"
        for event in result:
            assert topic in event["topics"]
            assert_fields_are_hex(event, self.ETH_HEX_FIELDS)
            assert_fields_are_specified_type(bool, event, self.ETH_BOOL_FIELDS)
            if method is Method.NEON_GET_LOGS:
                assert_fields_are_specified_type(int, event, self.NEON_INT_FIELDS)
                assert_fields_are_specified_type(str, event, self.NEON_HASH_FIELDS)

    @pytest.mark.parametrize("method", [Method.NEON_GET_LOGS, Method.ETH_GET_LOGS])
    @pytest.mark.parametrize(
        "event_filter, arg_filter, log_count",
        [
            (["Event2(string,string)"], None, 2),
            ([], ["text1"], 3),
            (["Event2(string,string)"], ["text2"], 1),
            (
                ["Event2(string,string)", "Event3(string,string,string)"],
                ["text2", "text3", "text1", "text5"],
                3,
            ),
            ([], None, 4),
        ],
    )
    def test_filter_log_by_topics(self, event_filter, arg_filter, log_count, method):
        event_caller, _ = self.web3_client.deploy_and_get_contract("common/EventCaller", "0.8.12", self.sender_account)

        arg1, arg2, arg3 = ("text1", "text2", "text3")
        topics = []
        if event_filter is not None:
            event_topics = []
            for item in event_filter:
                event_topics.append(cryptohex(item))
            topics.append(event_topics)
        if arg_filter is not None:
            arg_topics = []
            for item in arg_filter:
                arg_topics.append(cryptohex(item))
            topics.append(arg_topics)

        tx = self.make_contract_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.callEvent1(arg1).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_contract_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.callEvent2(arg1, arg2).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_contract_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.callEvent2(arg2, arg3).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_contract_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.callEvent3(arg1, arg2, arg3).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"address": event_caller.address, "topics": topics}
        response = self.proxy_api.send_rpc(method.value, params=params)

        assert (
            len(response["result"]) == log_count
        ), f"Expected {log_count} event logs, but found {len(response['result'])}"

        is_event_topic_in_list = False
        is_arg_topic_in_list = False
        for log in response["result"]:
            if topics[0]:
                for topic in topics[0]:
                    if topic in log["topics"]:
                        is_event_topic_in_list = True
            else:
                is_event_topic_in_list = True
            if len(topics) == 2:
                for topic in topics[1]:
                    if topic in log["topics"]:
                        is_arg_topic_in_list = True
            else:
                is_arg_topic_in_list = True

        assert is_event_topic_in_list, f"Filter by {topics} works incorrect. Response: {response}"
        assert is_arg_topic_in_list, f"Filter by {topics} works incorrect. Response: {response}"
