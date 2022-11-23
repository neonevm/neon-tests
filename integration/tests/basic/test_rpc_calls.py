import re
import typing as tp
from enum import Enum

import allure
import pytest
import sha3
import web3

from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers import rpc_checks
from utils import helpers
from utils.consts import Unit
from utils.helpers import gen_hash_of_block
from ui.libs import try_until

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
        keccak256 = sha3.keccak_256()
        keccak256.update(f"{event['name']}({input_types})".encode())
        topics.append(f"0x{keccak256.hexdigest()}")
    return topics


@allure.story("Basic: Json-RPC call tests")
class TestRpcCalls(BaseMixin):
    @pytest.fixture
    def send_erc20(self) -> tp.Any:
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20", "0.6.6", self.sender_account, constructor_args=[1000]
        )
        tx_receipt = self.web3_client.send_erc20(
            self.sender_account,
            self.recipient_account.address,
            amount=1,
            address=contract_deploy_tx["contractAddress"],
            abi=contract.abi,
        )
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        yield contract, contract_deploy_tx, tx_receipt

    @pytest.mark.parametrize(
        "params, raises",
        [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)],
    )
    def test_eth_call(self, params: tp.Union[Tag, None], raises: bool):
        """Verify implemented rpc calls work eth_call"""
        if params:
            params = [{"to": self.recipient_account.address, "data": hex(pow(10, 14))}, params.value]

        response = self.proxy_api.send_rpc("eth_call", params=params)

        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert response["result"] == "0x", f"Invalid response result, `{response['result']}`"

    @pytest.mark.parametrize(
        "params, raises",
        [(None, False), ("param", True)],
    )
    def test_eth_gas_price(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_gasPrice"""
        response = self.proxy_api.send_rpc("eth_gasPrice", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), f"Invalid current gas price `{response['result']}` in wei"

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
            (Tag.EARLIEST, None)
        ],
    )
    def test_eth_get_logs_via_tags(self, tag1: Tag, tag2: Tag, send_erc20: tp.Any):
        """Verify implemented rpc calls work eth_getLogs"""
        contract, deploy_tx, _ = send_erc20
        topics = get_event_signatures(contract.abi)
        params = {
            "address": deploy_tx.contractAddress,
            "topics": topics,
        }
        if tag1:
            params["fromBlock"] = tag1.value
        if tag2:
            params["toBlock"] = tag2.value
        response = self.proxy_api.send_rpc("eth_getLogs", params=params)
        assert "error" not in response
        if response["result"]:
            assert any(topic in response["result"][0]["topics"] for topic in topics)

    @pytest.mark.parametrize(
        "params, raises",
        [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)],
    )
    @pytest.mark.only_stands
    def test_eth_get_balance(self, params: tp.Union[Tag, str], raises: bool):
        """Verify implemented rpc calls work eth_getBalance"""
        response = self.proxy_api.send_rpc(
            "eth_getBalance", params=[self.sender_account.address, params.value if params else params]
        )
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), AssertMessage.WRONG_AMOUNT.value

    @pytest.mark.parametrize(
        "params, raises",
        [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)],
    )
    def test_eth_get_code(self, params: tp.Union[Tag, None], raises: bool):
        """Verify implemented rpc calls work eth_getCode"""
        if params:
            params = [self.sender_account.address, params.value]
        response = self.proxy_api.send_rpc("eth_getCode", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert response["result"] == "0x", f"Invalid result code {response['result']} at a given address."

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_web3_client_version(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work web3_clientVersion"""
        response = self.proxy_api.send_rpc("web3_clientVersion", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert "Neon" in response["result"], "Invalid response result"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_net_version(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work work net_version"""
        response = self.proxy_api.send_rpc("net_version", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert (
                    int(response["result"]) == self.web3_client._chain_id
            ), f"Invalid response result {response['result']}"

    @pytest.mark.parametrize(
        "params, raises",
        [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)],
    )
    def test_rpc_call_eth_get_transaction_count(self, params: tp.Union[Tag, None], raises: bool):
        """Verify implemented rpc calls work eth_getTransactionCount"""
        if params:
            self.send_neon(self.sender_account, self.recipient_account, 1)
            params = [self.sender_account.address, params.value]

        response = self.proxy_api.send_rpc("eth_getTransactionCount", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), AssertMessage.DOES_NOT_START_WITH_0X.value

    def test_rpc_call_eth_send_raw_transaction(self):
        """Verify implemented rpc calls work eth_sendRawTransaction"""
        transaction = self.create_tx_object(amount=1)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)
        response = self.proxy_api.send_rpc("eth_sendRawTransaction", params=signed_tx.rawTransaction.hex())
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result {response['result']}"

    @pytest.mark.parametrize(
        "params, raises",
        [(32, False), (16, True), (None, True)],
    )
    def test_rpc_call_eth_get_transaction_by_hash(self, params: tp.Union[int, None], raises: bool):
        """Verify implemented rpc calls work eth_getTransactionByHash"""
        if params:
            params = gen_hash_of_block(params)
        response = self.proxy_api.send_rpc(method="eth_getTransactionByHash", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert response["result"] is None, f"Invalid response: {response['result']}"

    def test_rpc_call_eth_get_transaction_receipt(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        transaction_hash = tx_receipt.transactionHash.hex()
        response = self.proxy_api.send_rpc(method="eth_getTransactionReceipt", params=transaction_hash)
        assert "error" not in response
        assert "result" in response, AssertMessage.DOES_NOT_CONTAIN_RESULT
        result = response["result"]
        expected_hex_fields = ['transactionHash', 'transactionIndex', 'blockNumber', 'blockHash', 'cumulativeGasUsed',
                               'gasUsed', 'logsBloom', 'status']
        for field in expected_hex_fields:
            assert rpc_checks.is_hex(result[field])
        assert result["status"] == '0x1', "Transaction status must be 0x1"
        assert result["transactionHash"] == transaction_hash
        assert result["blockHash"] == tx_receipt.blockHash.hex()
        assert result["from"].upper() == tx_receipt['from'].upper()
        assert result["to"].upper() == tx_receipt['to'].upper()
        assert result["contractAddress"] is None
        assert result["logs"] == []

    def test_rpc_call_eth_get_transaction_receipt_when_hash_doesnt_exist(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt when transaction hash doesn't exist"""
        response = self.proxy_api.send_rpc(method="eth_getTransactionReceipt", params=gen_hash_of_block(32))
        assert response['result'] is None, "Result should be None"

    def test_rpc_call_eth_get_transaction_receipt_with_incorrect_hash(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt when transaction hash is not correct"""
        transaction_hash = gen_hash_of_block(31)
        response = self.proxy_api.send_rpc(method="eth_getTransactionReceipt", params=transaction_hash)
        assert "error" in response
        assert response["error"]["message"] == "transaction-id is not hex"

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash(self, full_trx: bool):
        """Verify implemented rpc calls work eth_getBlockByHash"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        params = [tx_receipt.blockHash.hex(), full_trx]
        response = self.proxy_api.send_rpc(method="eth_getBlockByHash", params=params)
        rpc_checks.assert_block_fields(response, full_trx, tx_receipt)

    @pytest.mark.parametrize("hash, full_trx, msg",
                             [(gen_hash_of_block(31), False, "bad block hash"),
                              ("bad_hash", True, "bad block hash bad_hash")])
    def test_eth_get_block_by_hash_with_incorrect_hash(self, hash, full_trx, msg):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        params = [hash, full_trx]
        response = self.proxy_api.send_rpc(method="eth_getBlockByHash", params=params)
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == -32602
        assert msg in response["error"]["message"]

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash_with_not_existing_hash(self, full_trx):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        params = [gen_hash_of_block(32), full_trx]
        response = self.proxy_api.send_rpc(method="eth_getBlockByHash", params=params)
        assert response['result'] is None, "Result should be None"

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_number_via_numbers(self, full_trx):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        response = self.proxy_api.send_rpc(method="eth_getBlockByNumber",
                                           params=[tx_receipt.blockNumber, full_trx])
        rpc_checks.assert_block_fields(response, full_trx, tx_receipt)

    def test_eth_get_block_by_number_with_incorrect_data(self):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = self.proxy_api.send_rpc(method="eth_getBlockByNumber", params=['bad_tag', True])
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == -32602
        assert 'failed to parse block tag: bad_tag' in response["error"]["message"]

    @pytest.mark.parametrize("number, full_trx",
                             [(gen_hash_of_block(31), False),
                              (gen_hash_of_block(31), True),
                              (gen_hash_of_block(32), True),
                              (gen_hash_of_block(32), False)])
    def test_eth_get_block_by_number_with_not_exist_data(self, number, full_trx):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = self.proxy_api.send_rpc(method="eth_getBlockByNumber", params=[number, full_trx])
        assert response['result'] is None, "Result should be None"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_block_number(self, params: tp.Union[str, bool], raises: bool):
        """Verify implemented rpc calls work work eth_blockNumber"""
        response = self.proxy_api.send_rpc(method="eth_blockNumber", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), f"Invalid response result {response['result']}"

    @pytest.mark.parametrize(
        "params, raises", [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)]
    )
    def test_eth_get_storage_at(self, params: tp.Union[Tag, bool], raises: bool):
        """Verify implemented rpc calls work eht_getStorageAt"""
        if params:
            params = [self.sender_account.address, hex(1), params.value]
        response = self.proxy_api.send_rpc(method="eth_getStorageAt", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_mining(self, params, raises):
        """Verify implemented rpc calls work eth_mining"""
        response = self.proxy_api.send_rpc(method="eth_mining", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert isinstance(response["result"], bool), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_syncing(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_syncing"""
        response = self.proxy_api.send_rpc(method="eth_syncing", params=params)
        if hasattr(response, "result"):
            err_msg = f"Invalid response: {response.result}"
            if not isinstance(response["result"], bool):
                assert all(isinstance(block, int) for block in response["result"].values()), err_msg
            else:
                assert not response.result, err_msg

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_net_peer_count(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work net_peerCount"""
        response = self.proxy_api.send_rpc(method="net_peerCount", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize(
        "params, raises",
        [("0x6865", False), ("param", True), (None, True)],
    )
    def test_web3_sha3(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work web3_sha3"""
        response = self.proxy_api.send_rpc(method="web3_sha3", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert response["result"].startswith("e5105")

    @pytest.mark.parametrize(
        "params, raises",
        [(32, False), (16, True), (None, True)],
    )
    def test_eth_get_block_transaction_count_by_hash(self, params: tp.Union[int, None], raises: bool):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByHash"""
        if params:
            params = gen_hash_of_block(params)
        response = self.proxy_api.send_rpc(method="eth_getBlockTransactionCountByHash", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize(
        "params, raises",
        [(32, False), (Tag.EARLIEST.value, False), ("param", True), (None, True)],
    )
    def test_eth_get_block_transaction_count_by_number(self, params: tp.Union[int, str, None], raises: bool):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByNumber"""
        if isinstance(params, int):
            params = hex(params)
        response = self.proxy_api.send_rpc(method="eth_getBlockTransactionCountByNumber", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_get_work(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_getWork"""
        response = self.proxy_api.send_rpc(method="eth_getWork", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert len(response["result"]) >= 3, f"Invalid response result: {response['result']}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_hash_rate(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_hashrate"""
        response = self.proxy_api.send_rpc(method="eth_hashrate", params=params)
        if raises:
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            assert rpc_checks.is_hex(response["result"]), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("method", UNSUPPORTED_METHODS)
    def test_check_unsupported_methods(self, method: str):
        """Check that endpoint was not implemented"""
        response = self.proxy_api.send_rpc(method)
        assert "error" in response
        assert "message" in response["error"]
        assert response["error"]["message"] == f"method {method} is not supported", response

    @pytest.mark.parametrize(
        "quantity_tag,full_trx",
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
        params = [quantity_tag.value, full_trx]
        response = self.proxy_api.send_rpc(method="eth_getBlockByNumber", params=params)
        rpc_checks.assert_block_fields(response, full_trx, None, quantity_tag == Tag.PENDING)

    @pytest.mark.parametrize(
        "quantity, raises",
        [("0x0", False), ("0x5", True)])
    def test_eth_get_transaction_by_block_number_and_index(self, quantity: str, raises: bool):
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        params = [hex(tx_receipt.blockNumber), quantity]
        response = self.proxy_api.send_rpc(method="eth_getTransactionByBlockNumberAndIndex", params=params)
        if raises:
            assert response['result'] is None, "Result should be None"
        else:
            assert "error" not in response
            result = response["result"]
            expected_hex_fields = ['blockHash', 'blockNumber', 'hash', 'transactionIndex',
                                   'type', 'from', 'nonce', 'gasPrice', 'gas', 'to', 'value', 'v', 's', 'r']
            for field in expected_hex_fields:
                assert rpc_checks.is_hex(result[field])
            assert result["blockHash"] == tx_receipt.blockHash.hex()
            assert result["from"].upper() == tx_receipt['from'].upper()
            assert result["to"].upper() == tx_receipt['to'].upper()

    @pytest.mark.parametrize(
        "quantity, raises",
        [("0x0", False), ("0x5", True)])
    def test_eth_get_transaction_by_block_hash_and_index(self, quantity: str, raises: bool):
        """Verify implemented rpc calls work eth_getTransactionByBlockHashAndIndex"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        params = [tx_receipt.blockHash.hex(), quantity]

        response = self.proxy_api.send_rpc(method="eth_getTransactionByBlockHashAndIndex", params=params)
        if raises:
            assert response['result'] is None, "Result should be None"
        else:
            assert "error" not in response
            result = response["result"]
            expected_hex_fields = ['blockHash', 'blockNumber', 'hash', 'transactionIndex',
                                   'type', 'from', 'nonce', 'gasPrice', 'gas', 'to', 'value', 'v', 's', 'r']
            for field in expected_hex_fields:
                assert rpc_checks.is_hex(result[field])
            assert result["blockHash"] == tx_receipt.blockHash.hex()
            assert result["from"].upper() == tx_receipt['from'].upper()
            assert result["to"].upper() == tx_receipt['to'].upper()

    @pytest.mark.parametrize(
        "params, raises",
        [([Tag.LATEST.value, 0], False),
         (["param", 1], True),
         ([], True)])
    def test_eth_get_transaction_by_block_number_and_index_by_tag(self, params: tp.List[tp.Union[int, str]], raises: bool):
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""

        if params:
            params = list(map(lambda i: hex(i) if isinstance(i, int) else i, params))
            if params[0] == Tag.LATEST.value:
                tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
                self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex", params=params)
        if raises:
            assert "error" in response, f"Error not in response. Response : {response}"
        else:
            assert "error" not in response
            result = response["result"]
            expected_hex_fields = ['blockHash', 'blockNumber', 'hash', 'transactionIndex',
                                   'type', 'from', 'nonce', 'gasPrice', 'gas', 'to', 'value', 'v', 's', 'r']
            for field in expected_hex_fields:
                assert rpc_checks.is_hex(result[field])

    def test_get_evm_params(self):
        response = self.proxy_api.send_rpc(method="neon_getEvmParams", params=[])

        expected_fields = ['NEON_GAS_LIMIT_MULTIPLIER_NO_CHAINID', 'NEON_POOL_SEED', 'NEON_COMPUTE_BUDGET_UNITS',
                           'NEON_SEED_VERSION', 'NEON_EVM_STEPS_LAST_ITERATION_MAX', 'NEON_PAYMENT_TO_DEPOSIT',
                           'NEON_COMPUTE_UNITS', 'NEON_REQUEST_UNITS_ADDITIONAL_FEE', 'NEON_PKG_VERSION',
                           'NEON_HEAP_FRAME',
                           'NEON_ACCOUNT_SEED_VERSION', 'NEON_TOKEN_MINT', 'NEON_TREASURY_POOL_SEED',
                           'NEON_STORAGE_ENTRIES_IN_CONTRACT_ACCOUNT', 'NEON_EVM_STEPS_MIN', 'NEON_PAYMENT_TO_TREASURE',
                           'NEON_OPERATOR_PRIORITY_SLOTS', 'NEON_STATUS_NAME', 'NEON_REVISION', 'NEON_ADDITIONAL_FEE',
                           'NEON_CHAIN_ID', 'NEON_COMPUTE_BUDGET_HEAP_FRAME', 'NEON_POOL_COUNT', 'NEON_HOLDER_MSG_SIZE',
                           'NEON_TREASURY_POOL_COUNT', 'NEON_TOKEN_MINT_DECIMALS', 'NEON_EVM_ID']
        for field in expected_fields:
            assert field in response["result"], f"Field {field} is not in response: {response}"

    def test_neon_cli_version(self):
        response = self.proxy_api.send_rpc(method="neon_cli_version", params=[])
        pattern = r"Neon-cli/[vt]\d{1,2}.\d{1,2}.\d{1,2}.*"
        assert re.match(pattern, response["result"]), \
            f"Version format is not correct. Pattern: {pattern}; Response: {response}"


@allure.story("Basic: Json-RPC call tests - `eth_estimateGas`")
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
        counter = self.web3_client.eth.contract(abi=contract_interface["abi"], bytecode=contract_interface["bin"])
        # Build transaction
        transaction = counter.constructor(*constructor_args).buildTransaction(
            {
                "chainId": self.web3_client._chain_id,
                "gas": 0,
                "gasPrice": self.web3_client.gas_price(),
                "nonce": self.web3_client.eth.get_transaction_count(self.account.address),
                "value": 0,
            }
        )
        del transaction["to"]
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=transaction)
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result, `{response['result']}`"
        transaction["gas"] = int(response["result"], 16)
        # Deploy contract
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.account.key)
        tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        contract_deploy_tx = self.web3_client.eth.wait_for_transaction_receipt(tx)
        return self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

    def test_check_eth_estimate_gas_with_big_int(self, deploy_big_gas_requirements_contract: tp.Any) -> None:
        """Check eth_estimateGas request on contracts with big int"""
        big_gas_contract = deploy_big_gas_requirements_contract
        trx_big_gas = big_gas_contract.functions.checkBigGasRequirements().buildTransaction(
            {
                "chainId": self.web3_client._chain_id,
                "from": self.account.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.account.address),
                "gas": 0,
                "gasPrice": self.web3_client.gas_price(),
                "value": 0,
            }
        )
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=trx_big_gas)
        assert "error" not in response
        estimated_gas = int(response["result"], 16)
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result, `{response['result']}`"
        trx_big_gas["gas"] = estimated_gas
        signed_trx_big_gas = self.web3_client.eth.account.sign_transaction(trx_big_gas, self.account.key)
        raw_trx_big_gas = self.web3_client.eth.send_raw_transaction(signed_trx_big_gas.rawTransaction)
        deploy_trx_big_gas = self.web3_client.eth.wait_for_transaction_receipt(raw_trx_big_gas)
        assert deploy_trx_big_gas.get("status"), f"Transaction is incomplete: {deploy_trx_big_gas}"
        assert estimated_gas >= int(deploy_trx_big_gas["gasUsed"]), "Estimated Gas < Used Gas"
