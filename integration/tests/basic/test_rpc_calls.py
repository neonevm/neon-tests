import random
import re
import string
import typing as tp
from enum import Enum

import allure
import pytest
from eth_utils import keccak

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex, assert_fields_are_boolean, \
    assert_equal_fields
from integration.tests.services.helpers.basic import cryptohex
from utils import helpers
from utils.consts import Unit
from utils.helpers import gen_hash_of_block

"""
12.	Verify implemented rpc calls work
12.1.	eth_getBlockByHash		
12.2.	eth_getBlockByNumber		
12.11.	eth_blockNumber		
12.12.	eth_call		
12.13.	eth_estimateGas		
12.14.	eth_gasPrice		
12.22.	eth_getLogs		
12.30.	eth_getBalance		
12.32.	eth_getTransactionCount		
12.33.	eth_getCode		
12.35.	eth_sendRawTransaction		
12.36.	eth_getTransactionByHash		
12.39.	eth_getTransactionReceipt		
12.40.	eht_getStorageAt		
12.61.	web3_clientVersion		
12.63.	net_version
"""


class Tag(Enum):
    EARLIEST = "earliest"
    LATEST = "latest"
    PENDING = "pending"


GET_LOGS_TEST_DATA = [
    (Tag.LATEST.value, Tag.LATEST.value),
    (Tag.EARLIEST.value, Tag.LATEST.value),
    (Tag.PENDING.value, Tag.LATEST.value),
    (Tag.LATEST.value, Tag.EARLIEST.value),
    (Tag.LATEST.value, Tag.PENDING.value),
]

UNSUPPORTED_METHODS = [
    "eth_accounts",
    "eth_coinbase",
    "eth_compileLLL",
    "eth_compileSerpent",
    "eth_compileSolidity",
    "eth_getCompilers",
    "eth_getFilterChanges",
    "eth_getStorage",
    "eth_getUncleByBlockHashAndIndex",
    "eth_getUncleByBlockNumberAndIndex",
    "eth_getUncleCountByBlockHash",
    "eth_getUncleCountByBlockNumber",
    "eth_newBlockFilter",
    "eth_newFilter",
    "eth_newPendingTransactionFilter",
    "eth_protocolVersion",
    "eth_sendTransaction",
    "eth_sign",
    "eth_signTransaction",
    "eth_submitHashrate",
    "eth_submitWork",
    "eth_uninstallFilter",
    "shh_addToGroup",
    "shh_getFilterChanges",
    "shh_getMessages",
    "shh_hasIdentity",
    "shh_newFilter",
    "shh_newGroup",
    "shh_newIdentity",
    "shh_post",
    "shh_uninstallFilter",
    "shh_version",
]


def get_event_signatures(abi: tp.List[tp.Dict]) -> tp.List[str]:
    """Get topics as keccak256 from abi Events"""
    topics = []
    for event in filter(lambda item: item["type"] == "event", abi):
        input_types = ",".join(i["type"] for i in event["inputs"])
        signature = f"{event['name']}({input_types})"
        topics.append(f"0x{keccak(signature.encode()).hex()}")
    return topics


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC proxy calls work")
class TestRpcCalls(BaseMixin):
    _erc20_contract: tp.Optional[tp.Any] = None

    @pytest.fixture
    def erc20_contract(self) -> tp.Any:
        if not TestRpcCalls._erc20_contract:
            contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
                "ERC20/ERC20.sol",
                "0.8.8",
                self.sender_account,
                contract_name="ERC20",
                constructor_args=["Test Token", "TT", 1000],
            )

            tx_receipt = self.web3_client.send_erc20(
                self.sender_account,
                self.recipient_account.address,
                amount=1,
                address=contract_deploy_tx["contractAddress"],
                abi=contract.abi,
            )
            self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
            TestRpcCalls._erc20_contract = contract, contract_deploy_tx, tx_receipt
        return TestRpcCalls._erc20_contract

    def make_tx_object(self, sender=None) -> tp.Dict:
        if sender is None:
            sender = self.sender_account.address
        return {
            "chainId": self.web3_client._chain_id,
            "gasPrice": self.web3_client.gas_price(),
            "nonce": self.web3_client.eth.get_transaction_count(sender),
            "value": 0,
        }

    def test_eth_call_without_params(self):
        """Verify implemented rpc calls work eth_call without params"""
        response = self.proxy_api.send_rpc("eth_call")
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("tag", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST])
    def test_eth_call(self, tag):
        """Verify implemented rpc calls work eth_call"""
        params = [
            {"to": self.recipient_account.address, "data": hex(pow(10, 14))},
            tag.value,
        ]

        response = self.proxy_api.send_rpc("eth_call", params=params)
        assert "error" not in response
        assert (
                response["result"] == "0x"
        ), f"Invalid response result, `{response['result']}`"

    def test_rpc_call_eth_get_transaction_receipt_with_incorrect_hash(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt when transaction hash is not correct"""

        response = self.proxy_api.send_rpc(
            method="eth_getTransactionReceipt", params=gen_hash_of_block(31)
        )
        assert "error" in response
        assert response["error"]["message"] == "transaction-id is not hex"

    @pytest.mark.parametrize("param", [None, "param"])
    def test_eth_gas_price(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work eth_gasPrice"""
        response = self.proxy_api.send_rpc("eth_gasPrice", params=param)
        if param:
            assert "error" in response, "Error not in response"
            return None
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid current gas price `{response['result']}` in wei"

    @pytest.mark.parametrize(
        "param_fields", [("address", "topics"), ("address",), ("topics",)]
    )
    def test_eth_get_logs_blockhash(self, event_caller_contract, param_fields):
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b'\0')
        bol = True
        tx = self.make_tx_object()
        instruction_tx = event_caller_contract.functions.allTypes(
            self.sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)
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
        assert_fields_are_hex(response["result"][0],
                              ["transactionHash", "blockHash",
                               "blockNumber", "transactionIndex", "address",
                               "logIndex", "data", "transactionLogIndex"])
        assert_fields_are_boolean(response["result"][0], ["removed"])
        assert_equal_fields(response, receipt, ["transactionHash", "blockHash",
                                                "blockNumber", "transactionIndex", "address",
                                                "logIndex", "data", "transactionLogIndex"])

    def test_eth_get_logs_blockhash_empty_params(self, event_caller_contract):
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b'\0')
        bol = True
        tx = self.make_tx_object()
        instruction_tx = event_caller_contract.functions.allTypes(
            self.sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        params = {"blockHash": receipt["blockHash"].hex()}

        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        assert "error" not in response

        assert_fields_are_hex(response["result"][0],
                              ["transactionHash", "blockHash",
                               "blockNumber", "transactionIndex", "address",
                               "logIndex", "transactionLogIndex"])
        assert_fields_are_boolean(response["result"][0], ["removed"])
        assert_equal_fields(response, receipt, ["blockHash"])

    @pytest.mark.xfail(reason="NDEV-2237")
    @pytest.mark.parametrize(
        "tag1, tag2", [
            (Tag.EARLIEST, None),
            (None, Tag.LATEST),
        ]
    )
    def test_eth_get_logs_blockhash_negative_tags(self, event_caller_contract, tag1, tag2):
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b'\0')
        bol = True
        tx = self.make_tx_object()
        instruction_tx = event_caller_contract.functions.allTypes(
            self.sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)
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
        ("p_name", "p_value", "p_error"), [
            ("address", "0xc0ffee254729296a45a3885639AC7E10F9d54979", None),
            ("address", "12345", "bad address"),
            ("topics", "Invalid(address,uint256,string,bytes32,bool)", "bad topic"),
        ]
    )
    def test_get_rpc_logs_negative_params(self, event_caller_contract, p_name, p_value, p_error):
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b'\0')
        bol = True
        tx = self.make_tx_object()
        instruction_tx = event_caller_contract.functions.allTypes(
            self.sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)
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
            assert len(response["result"]) == 0, "should not find any logs since the wrong address was provided"
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
    def test_get_rpc_logs(self, event_caller_contract, param_fields, tag1, tag2):
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

        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b'\0')
        bol = True
        tx = self.make_tx_object()
        instruction_tx = event_caller_contract.functions.allTypes(
            self.sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)
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
            assert_fields_are_hex(response["result"][0],
                                  ["transactionHash", "blockHash",
                                   "blockNumber", "transactionIndex", "address",
                                   "logIndex", "data", "transactionLogIndex"])
            assert_fields_are_boolean(response["result"][0], ["removed"])
            if "address" in param_fields:
                assert response["result"][0]["address"] == receipt["to"].lower(), \
                    f"address from response {response['result'][0]['address']} " \
                    f"is not equal to address from receipt {receipt['to'].lower()}"

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    @pytest.mark.only_stands
    def test_eth_get_balance(self, param: tp.Union[Tag, None]):
        """Verify implemented rpc calls work eth_getBalance"""
        response = self.proxy_api.send_rpc(
            "eth_getBalance",
            params=[self.sender_account.address, param.value if param else param],
        )
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), AssertMessage.WRONG_AMOUNT.value

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    def test_eth_get_code(self, param: tp.Union[Tag, None]):
        """Verify implemented rpc calls work eth_getCode"""
        response = self.proxy_api.send_rpc(
            "eth_getCode",
            params=[self.sender_account.address, param.value] if param else param,
        )
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert (
                response["result"] == "0x"
        ), f"Invalid result code {response['result']} at a given address."

    @pytest.mark.parametrize("param", [None, "param"])
    def test_web3_client_version(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work web3_clientVersion"""
        response = self.proxy_api.send_rpc("web3_clientVersion", params=param)
        if param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert "Neon" in response["result"], "Invalid response result"

    @pytest.mark.parametrize("param", [None, "param"])
    def test_net_version(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work work net_version"""
        response = self.proxy_api.send_rpc("net_version", params=param)
        if param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert (
                int(response["result"]) == self.web3_client._chain_id
        ), f"Invalid response result {response['result']}"

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    def test_rpc_call_eth_get_transaction_count(self, param: tp.Union[Tag, None]):
        """Verify implemented rpc calls work eth_getTransactionCount"""
        if param:
            self.send_neon(self.sender_account, self.recipient_account, 1)
            param = [self.sender_account.address, param.value]
        response = self.proxy_api.send_rpc("eth_getTransactionCount", params=param)
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), AssertMessage.DOES_NOT_START_WITH_0X.value

    def test_rpc_call_eth_send_raw_transaction(self):
        """Verify implemented rpc calls work eth_sendRawTransaction"""
        transaction = self.create_tx_object(amount=1)

        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", params=signed_tx.rawTransaction.hex()
        )
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result {response['result']}"

    @pytest.mark.parametrize("param", [128, 32, 16, None])
    def test_rpc_call_eth_get_transaction_by_hash(self, param: tp.Union[int, None]):
        """Verify implemented rpc calls work eth_getTransactionByHash"""
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByHash",
            params=gen_hash_of_block(param) if param else param,
        )
        if not param or param != pow(2, 5):
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert response["result"] is None, f"Invalid response: {response['result']}"

    def test_rpc_call_eth_get_transaction_receipt(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        transaction_hash = tx_receipt.transactionHash.hex()
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionReceipt", params=transaction_hash
        )
        assert "error" not in response
        assert "result" in response, AssertMessage.DOES_NOT_CONTAIN_RESULT
        result = response["result"]
        expected_hex_fields = [
            "transactionHash",
            "transactionIndex",
            "blockNumber",
            "blockHash",
            "cumulativeGasUsed",
            "gasUsed",
            "logsBloom",
            "status",
        ]
        for field in expected_hex_fields:
            assert rpc_checks.is_hex(result[field])
        assert result["status"] == "0x1", "Transaction status must be 0x1"
        assert result["transactionHash"] == transaction_hash
        assert result["blockHash"] == tx_receipt.blockHash.hex()
        assert result["from"].upper() == tx_receipt["from"].upper()
        assert result["to"].upper() == tx_receipt["to"].upper()
        assert result["contractAddress"] is None
        assert result["logs"] == []

    def test_rpc_call_eth_get_transaction_receipt_when_hash_doesnt_exist(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt when transaction hash doesn't exist"""
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionReceipt", params=gen_hash_of_block(32)
        )
        assert response["result"] is None, "Result should be None"

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash(self, full_trx: bool):
        """Verify implemented rpc calls work eth_getBlockByHash"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        params = [tx_receipt.blockHash.hex(), full_trx]
        response = self.proxy_api.send_rpc(method="eth_getBlockByHash", params=params)
        rpc_checks.assert_block_fields(response, full_trx, tx_receipt)

    @pytest.mark.parametrize(
        "hash_len, full_trx, msg",
        [(31, False, "bad block hash"), ("bad_hash", True, "bad block hash bad_hash")],
    )
    def test_eth_get_block_by_hash_with_incorrect_hash(self, hash_len, full_trx, msg):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        block_hash = (
            gen_hash_of_block(hash_len) if isinstance(hash_len, int) else hash_len
        )
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByHash", params=[block_hash, full_trx]
        )
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == -32602
        assert msg in response["error"]["message"]

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash_with_not_existing_hash(self, full_trx):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByHash", params=[gen_hash_of_block(32), full_trx]
        )
        assert response["result"] is None, "Result should be None"

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_number_via_numbers(self, full_trx):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByNumber", params=[hex(tx_receipt.blockNumber), full_trx]
        )
        rpc_checks.assert_block_fields(response, full_trx, tx_receipt)

    def test_eth_get_block_by_number_with_incorrect_data(self):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByNumber", params=["bad_tag", True]
        )
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == -32602
        assert "failed to parse block tag: bad_tag" in response["error"]["message"]

    @pytest.mark.parametrize(
        "number, full_trx",
        [
            (5, False),
            (31, False),
            (31, True),
            (32, True),
            (32, False),
        ],
    )
    def test_eth_get_block_by_number_with_not_exist_data(self, number, full_trx):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByNumber", params=[gen_hash_of_block(number), full_trx]
        )
        assert response["result"] is None, "Result should be None"

    @pytest.mark.parametrize("param", [None, "param"])
    def test_eth_block_number(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work work eth_blockNumber"""
        response = self.proxy_api.send_rpc(method="eth_blockNumber", params=param)
        if param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result {response['result']}"

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    def test_eth_get_storage_at(self, param: tp.Union[Tag, None]):
        """Verify implemented rpc calls work eht_getStorageAt"""
        response = self.proxy_api.send_rpc(
            method="eth_getStorageAt",
            params=[self.sender_account.address, hex(1), param.value]
            if param
            else param,
        )
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("param", [None, "param"])
    def test_eth_mining(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work eth_mining"""
        response = self.proxy_api.send_rpc(method="eth_mining", params=param)
        if param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert isinstance(
            response["result"], bool
        ), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("param", [None, "param"])
    def test_eth_syncing(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work eth_syncing"""
        response = self.proxy_api.send_rpc(method="eth_syncing", params=param)
        if hasattr(response, "result"):
            err_msg = f"Invalid response: {response.result}"
            if not isinstance(response["result"], bool):
                assert all(
                    isinstance(block, int) for block in response["result"].values()
                ), err_msg
            else:
                assert not response.result, err_msg

    @pytest.mark.parametrize("param", [None, "param"])
    def test_net_peer_count(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work net_peerCount"""
        response = self.proxy_api.send_rpc(method="net_peerCount", params=param)
        if param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("param", ["0x6865", "param", None, True])
    def test_web3_sha3(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work web3_sha3"""
        response = self.proxy_api.send_rpc(method="web3_sha3", params=param)
        if isinstance(param, str) and param.startswith("0"):
            assert "error" not in response
            assert response["result"][2:].startswith("e5105")
        else:
            assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("param", [128, 32, 16, None])
    def test_eth_get_block_transaction_count_by_hash(self, param: tp.Union[int, None]):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByHash"""
        response = self.proxy_api.send_rpc(
            method="eth_getBlockTransactionCountByHash",
            params=gen_hash_of_block(param) if param else param,
        )
        if not param or param != pow(2, 5):
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("param", [32, Tag.EARLIEST.value, "param", None])
    def test_eth_get_block_transaction_count_by_number(
            self, param: tp.Union[int, str, None]
    ):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByNumber"""
        if isinstance(param, int):
            param = hex(param)
        response = self.proxy_api.send_rpc(
            method="eth_getBlockTransactionCountByNumber", params=param
        )
        if not param or param == "param":
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("param", [None, "param"])
    def test_eth_get_work(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work eth_getWork"""
        response = self.proxy_api.send_rpc(method="eth_getWork", params=param)
        if param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert (
                len(response["result"]) >= 3
        ), f"Invalid response result: {response['result']}"

    @pytest.mark.parametrize("param", [None, "param"])
    def test_eth_hash_rate(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work eth_hashrate"""
        response = self.proxy_api.send_rpc(method="eth_hashrate", params=param)
        if param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("method", UNSUPPORTED_METHODS)
    def test_check_unsupported_methods(self, method: str):
        """Check that endpoint was not implemented"""
        response = self.proxy_api.send_rpc(method)
        assert "error" in response
        assert "message" in response["error"]
        assert (
                response["error"]["message"] == f"the method {method} does not exist/is not available"
        ), response

    @pytest.mark.parametrize(
        "quantity_tag, full_trx",
        [
            (Tag.EARLIEST, True),
            (Tag.EARLIEST, False),
            (Tag.LATEST, True),
            (Tag.LATEST, False),
            (Tag.PENDING, True),
            (Tag.PENDING, False),
        ],
    )
    def test_eth_get_block_by_number_via_tags(self, quantity_tag: Tag, full_trx: bool):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        self.send_neon(self.sender_account, self.recipient_account, 10)
        params = [quantity_tag.value, full_trx]
        response = self.proxy_api.send_rpc(method="eth_getBlockByNumber", params=params)
        rpc_checks.assert_block_fields(
            response, full_trx, None, quantity_tag == Tag.PENDING
        )

    @pytest.mark.parametrize("valid_index", [True, False])
    def test_eth_get_transaction_by_block_number_and_index(self, valid_index: bool):
        amount = 10
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, amount=amount)
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        transaction_index = (
            hex(tx_receipt.transactionIndex) if valid_index else hex(999)
        )
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex",
            params=[hex(tx_receipt.blockNumber), transaction_index],
        )
        if not valid_index:
            assert response["result"] is None, "Result should be None"
        else:
            assert "error" not in response
            result = response["result"]
            expected_hex_fields = [
                "blockHash",
                "blockNumber",
                "hash",
                "transactionIndex",
                "type",
                "from",
                "nonce",
                "gasPrice",
                "gas",
                "to",
                "value",
                "v",
                "s",
                "r",
            ]
            for field in expected_hex_fields:
                assert rpc_checks.is_hex(result[field])
            assert result["blockHash"] == tx_receipt.blockHash.hex()
            assert result["from"].upper() == tx_receipt["from"].upper()
            assert result["to"].upper() == tx_receipt["to"].upper()
            assert result["value"] == hex(self.web3_client.to_wei(amount, Unit.ETHER))

    @pytest.mark.parametrize("valid_index", [True, False])
    def test_eth_get_transaction_by_block_hash_and_index(self, valid_index: bool):
        """Verify implemented rpc calls work eth_getTransactionByBlockHashAndIndex"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        transaction_index = (
            hex(tx_receipt.transactionIndex) if valid_index else hex(999)
        )
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByBlockHashAndIndex",
            params=[tx_receipt.blockHash.hex(), transaction_index],
        )
        if not valid_index:
            assert response["result"] is None, "Result should be None"
        else:
            assert "error" not in response
            result = response["result"]
            expected_hex_fields = [
                "blockHash",
                "blockNumber",
                "hash",
                "transactionIndex",
                "type",
                "from",
                "nonce",
                "gasPrice",
                "gas",
                "to",
                "value",
                "v",
                "s",
                "r",
            ]
            for field in expected_hex_fields:
                assert rpc_checks.is_hex(result[field])
            assert result["blockHash"] == tx_receipt.blockHash.hex()
            assert result["from"].upper() == tx_receipt["from"].upper()
            assert result["to"].upper() == tx_receipt["to"].upper()

    @pytest.mark.parametrize("tag", [Tag.LATEST.value, Tag.EARLIEST.value, "param"])
    def test_eth_get_transaction_by_block_number_and_index_by_tag(self, tag: str):
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex",
            params=[tag, hex(tx_receipt.transactionIndex)],
        )
        if tag == "param":
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            result = response["result"]
            if result:
                expected_hex_fields = [
                    "blockHash",
                    "blockNumber",
                    "hash",
                    "transactionIndex",
                    "type",
                    "from",
                    "nonce",
                    "gasPrice",
                    "gas",
                    "value",
                    "v",
                    "s",
                    "r",
                ]
                for field in expected_hex_fields:
                    assert rpc_checks.is_hex(result[field]), f"Field {field} must be hex but '{result[field]}'"

    def test_get_evm_params(self):
        response = self.proxy_api.send_rpc(method="neon_getEvmParams", params=[])

        expected_fields = [
            "NEON_GAS_LIMIT_MULTIPLIER_NO_CHAINID",
            "NEON_POOL_SEED",
            "NEON_COMPUTE_BUDGET_UNITS",
            "NEON_SEED_VERSION",
            "NEON_EVM_STEPS_LAST_ITERATION_MAX",
            "NEON_PAYMENT_TO_DEPOSIT",
            "NEON_COMPUTE_UNITS",
            "NEON_REQUEST_UNITS_ADDITIONAL_FEE",
            "NEON_PKG_VERSION",
            "NEON_HEAP_FRAME",
            "NEON_ACCOUNT_SEED_VERSION",
            "NEON_TOKEN_MINT",
            "NEON_TREASURY_POOL_SEED",
            "NEON_STORAGE_ENTRIES_IN_CONTRACT_ACCOUNT",
            "NEON_EVM_STEPS_MIN",
            "NEON_PAYMENT_TO_TREASURE",
            "NEON_OPERATOR_PRIORITY_SLOTS",
            "NEON_STATUS_NAME",
            "NEON_REVISION",
            "NEON_ADDITIONAL_FEE",
            "NEON_CHAIN_ID",
            "NEON_COMPUTE_BUDGET_HEAP_FRAME",
            "NEON_POOL_COUNT",
            "NEON_HOLDER_MSG_SIZE",
            "NEON_TREASURY_POOL_COUNT",
            "NEON_TOKEN_MINT_DECIMALS",
            "NEON_EVM_ID",
        ]
        for field in expected_fields:
            assert (
                    field in response["result"]
            ), f"Field {field} is not in response: {response}"

    def test_neon_cli_version(self):
        response = self.proxy_api.send_rpc(method="neon_cli_version", params=[])
        pattern = r"Neon-cli/[vt]\d{1,2}.\d{1,2}.\d{1,2}.*"
        assert re.match(
            pattern, response["result"]
        ), f"Version format is not correct. Pattern: {pattern}; Response: {response}"

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
    def test_get_neon_logs(self, event_caller_contract, param_fields, tag1, tag2):
        number = random.randint(1, 100)
        text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        bytes_array = text.encode().ljust(32, b'\0')
        bol = True
        tx = self.make_tx_object()
        instruction_tx = event_caller_contract.functions.allTypes(
            self.sender_account.address, number, text, bytes_array, bol
        ).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)
        topic = (
                "0x" + keccak(text="AllTypes(address,uint256,string,bytes32,bool)").hex()
        )

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
            assert_fields_are_hex(response["result"][0],
                                  ["transactionHash", "blockHash",
                                   "blockNumber", "transactionIndex",
                                   "address", "logIndex", "data",
                                   "transactionLogIndex"])

    @pytest.mark.parametrize("method", ["neon_getLogs", "eth_getLogs"])
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
        event_caller, _ = self.web3_client.deploy_and_get_contract(
            "EventCaller", "0.8.12", self.sender_account
        )

        arg1, arg2, arg3 = ("text1", "text2", "text3")
        topics = []
        if event_filter is not None:
            event_topics = []
            for item in event_filter:
                event_topics.append("0x" + keccak(text=item).hex())
            topics.append(event_topics)
        if arg_filter is not None:
            arg_topics = []
            for item in arg_filter:
                arg_topics.append("0x" + keccak(text=item).hex())
            topics.append(arg_topics)

        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.callEvent1(arg1).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.callEvent2(arg1, arg2).build_transaction(
            tx
        )
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.callEvent2(arg2, arg3).build_transaction(
            tx
        )
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object(self.sender_account.address)
        instruction_tx = event_caller.functions.callEvent3(
            arg1, arg2, arg3
        ).build_transaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        response = self.proxy_api.send_rpc(
            method,
            params={
                "address": event_caller.address,
                "topics": topics,
            },
        )

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

        assert (
            is_event_topic_in_list
        ), f"Filter by {topics} works incorrect. Response: {response}"
        assert (
            is_arg_topic_in_list
        ), f"Filter by {topics} works incorrect. Response: {response}"


@allure.feature("JSON-RPC validation")
@allure.story("Verify eth_estimateGas RPC call")
class TestRpcCallsMoreComplex(BaseMixin):
    account: "eth_account.signers.local.LocalAccount" = None

    @pytest.fixture(params=[(850000, 15000), (8500000, 150000), (8500000, 150000)])
    def constructor_args(self, request: tp.Any) -> tp.List[int]:
        return request.param

    @pytest.fixture(params=["BigGasFactory1", "BigGasFactory2"])
    def deploy_big_gas_requirements_contract(
            self, request: tp.Any, constructor_args: tp.List[int]
    ) -> "web3._utils.datatypes.Contract":
        """Deploy contracts"""
        self.account = self.sender_account
        #  contract
        contract_interface = helpers.get_contract_interface(
            contract="NDEV49", version="0.8.10", contract_name=request.param
        )
        counter = self.web3_client.eth.contract(
            abi=contract_interface["abi"], bytecode=contract_interface["bin"]
        )
        # Build transaction
        transaction = counter.constructor(*constructor_args).build_transaction(
            {
                "chainId": self.web3_client._chain_id,
                "gas": 0,
                "gasPrice": hex(self.web3_client.gas_price()),
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.account.address
                ),
                "value": "0x0",
            }
        )
        del transaction["to"]
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=transaction)
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result, `{response['result']}`"
        transaction["gas"] = int(response["result"], 16)
        # Deploy contract
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.account.key
        )
        tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        contract_deploy_tx = self.web3_client.eth.wait_for_transaction_receipt(tx)
        return self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

    def test_check_eth_estimate_gas_with_big_int(
            self, deploy_big_gas_requirements_contract: tp.Any
    ) -> None:
        """Check eth_estimateGas request on contracts with big int"""
        big_gas_contract = deploy_big_gas_requirements_contract
        trx_big_gas = (
            big_gas_contract.functions.checkBigGasRequirements().build_transaction(
                {
                    "chainId": self.web3_client._chain_id,
                    "from": self.account.address,
                    "nonce": self.web3_client.eth.get_transaction_count(
                        self.account.address
                    ),
                    "gas": "0x0",
                    "gasPrice": hex(self.web3_client.gas_price()),
                    "value": "0x0",
                }
            )
        )
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=trx_big_gas)
        assert "error" not in response
        estimated_gas = int(response["result"], 16)
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result, `{response['result']}`"
        trx_big_gas["gas"] = estimated_gas
        signed_trx_big_gas = self.web3_client.eth.account.sign_transaction(
            trx_big_gas, self.account.key
        )
        raw_trx_big_gas = self.web3_client.eth.send_raw_transaction(
            signed_trx_big_gas.rawTransaction
        )
        deploy_trx_big_gas = self.web3_client.eth.wait_for_transaction_receipt(
            raw_trx_big_gas
        )
        assert deploy_trx_big_gas.get(
            "status"
        ), f"Transaction is incomplete: {deploy_trx_big_gas}"
        assert estimated_gas >= int(
            deploy_trx_big_gas["gasUsed"]
        ), "Estimated Gas < Used Gas"
