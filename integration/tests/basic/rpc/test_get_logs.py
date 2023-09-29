import allure
import pytest
import random
import string

from web3.types import TxParams

from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex, assert_fields_are_boolean, \
    assert_equal_fields
from integration.tests.basic.rpc.test_rpc_calls import Tag
from integration.tests.services.helpers.basic import cryptohex


@allure.feature("JSON-RPC-GET-LOGS validation")
@allure.story("Verify getLogs method")
class TestGetLogs(BaseMixin):

    def create_all_types_instruction(self, event_caller_contract) -> TxParams:
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b"\0")
        bol = True
        tx = self.make_tx_object()
        instruction_tx = event_caller_contract.functions.allTypes(
            self.sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)

        return instruction_tx

    @pytest.mark.parametrize(
        "param_fields", [("address", "topics"), ("address",), ("topics",)]
    )
    def test_eth_get_logs_blockhash(self, event_caller_contract, param_fields):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"blockHash": receipt["blockHash"].hex()}

        topic = False
        if "address" in param_fields:
            params["address"] = event_caller_contract.address
        if "topics" in param_fields:
            topic = cryptohex("AllTypes(address,uint256,string,bytes32,bool)")
            params["topics"] = [topic]

        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        assert "error" not in response
        if topic:
            assert topic in response["result"][0]["topics"]
        assert_fields_are_hex(
            response["result"][0],
            [
                "transactionHash",
                "blockHash",
                "blockNumber",
                "transactionIndex",
                "address",
                "logIndex",
                "data",
                "transactionLogIndex",
            ],
        )
        assert_fields_are_boolean(response["result"][0], ["removed"])

    def test_eth_get_logs_blockhash_empty_params(self, event_caller_contract):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"blockHash": receipt["blockHash"].hex()}

        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        assert "error" not in response

        assert_fields_are_hex(
            response["result"][0],
            [
                "transactionHash",
                "blockHash",
                "blockNumber",
                "transactionIndex",
                "address",
                "logIndex",
                "transactionLogIndex",
            ],
        )
        assert_fields_are_boolean(response["result"][0], ["removed"])
        assert_equal_fields(response, receipt, ["blockHash"])

    @pytest.mark.xfail(reason="NDEV-2237")
    @pytest.mark.parametrize(
        "tag1, tag2",
        [
            (Tag.EARLIEST, None),
            (None, Tag.LATEST),
        ],
    )
    def test_eth_get_logs_blockhash_negative_tags(self, event_caller_contract, tag1, tag2):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"blockHash": receipt["blockHash"].hex()}
        if tag1:
            params["fromBlock"] = tag1.value
        if tag2:
            params["toBlock"] = tag2.value

        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        assert "error" in response
        assert "message" in response
        assert "invalid filter" in response["message"]

    @pytest.mark.parametrize(
        ("p_name", "p_value", "p_error"),
        [
            ("address", "0xc0ffee254729296a45a3885639AC7E10F9d54979", None),
            ("address", "12345", "bad address"),
            ("topics", "Invalid(address,uint256,string,bytes32,bool)", "bad topic"),
        ],
    )
    def test_eth_get_logs_negative_params(self, event_caller_contract, p_name, p_value, p_error):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"fromBlock": Tag.EARLIEST.value, "toBlock": Tag.LATEST.value}
        if p_name == "address":
            params["address"] = p_value
        if p_name == "topics":
            params["topics"] = [p_value]

        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        if not p_error and p_name == "address":
            assert "error" not in response
            assert "result" in response
            assert (
                    len(response["result"]) == 0
            ), "should not find any logs since the wrong address was provided"
        else:
            assert "error" in response
            assert "message" in response["error"]
            assert p_error in response["error"]["message"]

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
    @pytest.mark.parametrize(
        "param_fields", [("address", "topics"), ("address",), ("topics",)]
    )
    def test_eth_get_logs(self, event_caller_contract, param_fields, tag1, tag2):
        params = {}
        block_number = False
        if isinstance(tag1, int) or isinstance(tag2, int):
            response = self.proxy_api.send_rpc(method="eth_blockNumber")
            assert "result" in response
            block_number = int(response["result"], 16)
        if tag1 or isinstance(tag1, int):
            params["fromBlock"] = (
                hex(block_number + tag1) if isinstance(tag1, int) else tag1.value
            )
        if tag2 or isinstance(tag2, int):
            params["toBlock"] = (
                hex(block_number + tag2) if isinstance(tag2, int) else tag2.value
            )

        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        topic = False
        if "address" in param_fields:
            params["address"] = event_caller_contract.address
        if "topics" in param_fields:
            topic = cryptohex("AllTypes(address,uint256,string,bytes32,bool)")
            params["topics"] = [topic]

        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        assert "error" not in response
        if response["result"]:
            if topic:
                assert topic in response["result"][0]["topics"]
            assert_fields_are_hex(
                response["result"][0],
                [
                    "transactionHash",
                    "blockHash",
                    "blockNumber",
                    "transactionIndex",
                    "address",
                    "logIndex",
                    "data",
                    "transactionLogIndex",
                ],
            )
            assert_fields_are_boolean(response["result"][0], ["removed"])
            if "address" in param_fields:
                assert response["result"][0]["address"] == receipt["to"].lower(), (
                    f"address from response {response['result'][0]['address']} "
                    f"is not equal to address from receipt {receipt['to'].lower()}"
                )

    def test_eth_get_logs_eq_val(self, event_caller_contract):
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {
            "blockHash": receipt["blockHash"].hex(),
            "address": event_caller_contract.address,
        }
        topic = cryptohex("AllTypes(address,uint256,string,bytes32,bool)")
        params["topics"] = [topic]

        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        assert "error" not in response
        assert topic in response["result"][0]["topics"]
        assert_fields_are_hex(
            response["result"][0],
            [
                "transactionHash",
                "blockHash",
                "blockNumber",
                "transactionIndex",
                "address",
                "logIndex",
                "data",
                "transactionLogIndex",
            ],
        )

        assert_fields_are_boolean(response["result"][0], ["removed"])
        assert_equal_fields(
            response,
            receipt,
            [
                "transactionHash",
                "blockHash",
                "blockNumber",
                "transactionIndex",
                "address",
                "logIndex",
                "data",
                "transactionLogIndex",
            ],
        )

    def test_eth_get_logs_list_of_addresses(self, event_caller_contract):
        event_caller2, _ = self.web3_client.deploy_and_get_contract(  # we need 2nd contract to check list of addresses
            "EventCaller", "0.8.12", self.sender_account
        )

        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        tx = self.make_tx_object()
        # transaction for first contract
        instruction_tx = event_caller_contract.functions.callEvent1(text).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx2 = self.make_tx_object()
        # transaction for second contract
        instruction_tx2 = event_caller2.functions.callEvent1(text).build_transaction(tx2)
        self.web3_client.send_transaction(self.sender_account, instruction_tx2)

        params = {"address": [event_caller_contract.address, event_caller2.address]}  # list of addresses
        topic = cryptohex("Event1(string)")
        params["topics"] = [topic, cryptohex(text)]

        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        assert "error" not in response
        assert len(response["result"]) == 2, \
            f"there should be 2 logs events from 2 contract, but got {len(response['result'])}"
        for event in response["result"]:
            assert topic in event["topics"]
            assert_fields_are_hex(event,
                                  ["transactionHash", "blockHash",
                                   "blockNumber", "transactionIndex", "address",
                                   "logIndex", "transactionLogIndex"])
            assert_fields_are_boolean(event, ["removed"])

    @pytest.mark.parametrize(
        "tag1, tag2",
        [
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
    @pytest.mark.parametrize(
        "param_fields", [("address", "topics"), ("address",), ("topics",)]
    )
    def test_neon_get_logs(self, event_caller_contract, param_fields, tag1, tag2):
        """Verify neon specific method: neon_getLogs"""
        instruction_tx = self.create_all_types_instruction(event_caller_contract)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)
        topic = cryptohex("AllTypes(address,uint256,string,bytes32,bool)")

        params = {}
        if "address" in param_fields:
            params["address"] = event_caller_contract.address
        if "topics" in param_fields:
            params["topics"] = [topic]

        if tag1:
            params["fromBlock"] = tag1.value
        if tag2:
            params["toBlock"] = tag2.value

        response = self.proxy_api.send_rpc("neon_getLogs", params=params)
        assert "error" not in response
        if response["result"]:
            assert topic in response["result"][0]["topics"]
            assert_fields_are_hex(
                response["result"][0],
                [
                    "transactionHash",
                    "blockHash",
                    "blockNumber",
                    "transactionIndex",
                    "address",
                    "logIndex",
                    "data",
                    "transactionLogIndex",
                ],
            )