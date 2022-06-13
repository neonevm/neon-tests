import typing as tp
from enum import Enum

import allure
import pytest

from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.helpers.unit import Unit
from integration.tests.basic.model import model as request_models
from integration.tests.basic.test_data import input_data

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


@allure.story("Basic: Json-RPC call tests")
class TestRpcCalls(BaseMixin):
    @staticmethod
    def is_hex(hex_data: str) -> bool:
        try:
            int(hex_data, 16)
            return True
        except (ValueError, TypeError):
            return False

    def assert_rpc_response(
        self,
        method: str,
        params: tp.Optional[tp.Any] = None,
        err_message: str = "",
        raises: bool = False,
    ) -> tp.Union[request_models.JsonRpcResponse, request_models.JsonRpcErrorResponse]:
        """Verify eth endpoints responses"""
        if not isinstance(params, tp.List):
            params = [params]
        payloads = getattr(RpcRequestFactory(), method)(*params)
        response = self.json_rpc_client.do_call(payloads)
        if raises:
            if err_message and not isinstance(err_message, str):
                err_message = err_message.value
            self.assert_expected_raises(response, err_message)
        else:
            assert isinstance(
                response, request_models.JsonRpcResponse
            ), f"rpc call is failed: {response.error.get('message')}"
            assert response.id == payloads.id, AssertMessage.WRONG_ID.value
        return response

    @pytest.mark.parametrize(
        "params, raises",
        [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)],
    )
    def test_eth_call(self, params: tp.Union[Tag, None], raises: bool):
        """Verify implemented rpc calls work eth_call"""
        if params:
            params = [{"to": self.recipient_account.address, "data": hex(pow(10, 14))}, params.value]
        response = self.assert_rpc_response("eth_call", params=params, raises=raises)
        if hasattr(response, "result"):
            assert response.result == "0x", f"Invalid response result, `{response.result}`"

    @pytest.mark.parametrize(
        "params, raises",
        [(hex(1), False), (None, True)],
    )
    def test_eth_estimate_gas(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_estimateGas"""
        if params:
            params = {"from": self.sender_account.address, "to": self.recipient_account.address, "value": params}
        response = self.assert_rpc_response("eth_estimateGas", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.is_hex(response.result), f"Invalid the amount {response.result} of gas used."

    @pytest.mark.parametrize(
        "params, raises",
        [(None, False), ("param", True)],
    )
    def test_eth_gas_price(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_gasPrice"""
        response = self.assert_rpc_response("eth_gasPrice", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.is_hex(response.result), f"Invalid current gas price `{response.result}` in wei"

    @pytest.mark.parametrize("params, raises", [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False)])
    def test_eth_get_logs_via_tags(self, params: Tag, raises: bool):
        """Verify implemented rpc calls work eth_getLogs"""
        params = {"fromBlock": params.value, "toBlock": params.value, "address": self.sender_account.address}
        self.assert_rpc_response("eth_getLogs", params=params, raises=raises)

    @pytest.mark.parametrize("params, raises", [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False)])
    def test_eth_get_logs_via_numbers(self, params: Tag, raises: bool):
        """Verify implemented rpc calls work eth_getLogs"""
        params = {"fromBlock": 1, "toBlock": params.value, "address": self.sender_account.address}
        self.assert_rpc_response("eth_getLogs", params=params, raises=raises)

    @pytest.mark.parametrize(
        "params, raises",
        [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)],
    )
    @pytest.mark.only_stands
    def test_eth_get_balance(self, params: tp.Union[Tag, str], raises: bool):
        """Verify implemented rpc calls work eth_getBalance"""
        response = self.assert_rpc_response(
            "eth_getBalance", params=[self.sender_account.address, params.value if params else params], raises=raises
        )
        if hasattr(response, "result"):
            assert self.is_hex(response.result), AssertMessage.WRONG_AMOUNT.value

    @pytest.mark.parametrize(
        "params, raises",
        [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)],
    )
    def test_eth_get_code(self, params: tp.Union[Tag, None], raises: bool):
        """Verify implemented rpc calls work eth_getCode"""
        if params:
            params = [self.sender_account.address, params.value]
        response = self.assert_rpc_response("eth_getCode", params=params, raises=raises)
        if hasattr(response, "result"):
            assert response.result == "0x", f"Invalid result code {response.result} at a given address."

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_web3_client_version(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work web3_clientVersion"""
        response = self.assert_rpc_response("web3_clientVersion", params=params, raises=raises)
        if hasattr(response, "result"):
            assert "Neon" in response.result, "Invalid response result"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_net_version(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work work net_version"""
        response = self.assert_rpc_response("net_version", params=params, raises=raises)
        if hasattr(response, "result"):
            response.result == self.web3_client._chain_id, f"Invalid response result {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)],
    )
    def test_rpc_call_eth_get_transaction_count(self, params: tp.Union[Tag, None], raises: bool):
        """Verify implemented rpc calls work eth_getTransactionCount"""
        if params:
            self.process_transaction(self.sender_account, self.recipient_account, 1)
            params = [self.sender_account.address, params.value]

        response = self.assert_rpc_response(
            "eth_getTransactionCount",
            params=params,
            raises=raises,
        )
        if hasattr(response, "result"):
            assert self.is_hex(response.result), AssertMessage.DOES_NOT_START_WITH_0X.value

    def test_rpc_call_eth_send_raw_transaction(self):
        """Verify implemented rpc calls work eth_sendRawTransaction"""

        transaction = {
            "from": self.sender_account.address,
            "to": self.recipient_account.address,
            "value": self.web3_client.toWei(1, Unit.ETHER),
            "chainId": self.web3_client._chain_id,
            "gasPrice": self.web3_client.gas_price(),
            "gas": 0,
            "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)
        response = self.assert_rpc_response(
            "eth_sendRawTransaction", params=signed_tx.rawTransaction.hex(), raises=False
        )
        assert self.is_hex(response.result), f"Invalid response result {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [(32, False), (16, True), (None, True)],
    )
    def test_rpc_call_eth_get_transaction_by_hash(self, params: tp.Union[int, None], raises: bool):
        """Verify implemented rpc calls work eth_getTransactionByHash"""
        if params:
            params = input_data.gen_hash_of_block(params)
        response = self.assert_rpc_response(method="eth_getTransactionByHash", params=params, raises=raises)
        if hasattr(response, "result"):
            assert response.result is None, f"Invalid response: {response.result}"

    def test_rpc_call_eth_get_transaction_receipt(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt"""

        tx_receipt = self.process_transaction(self.sender_account, self.recipient_account, 10)
        response = self.assert_rpc_response(
            method="eth_getTransactionReceipt", params=tx_receipt.transactionHash.hex(), raises=False
        )
        assert self.assert_result_object(response), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_eth_get_block_by_hash(self):
        """Verify implemented rpc calls work eth_getBlockByHash"""

        tx_receipt = self.process_transaction(self.sender_account, self.recipient_account, 10)

        params = [tx_receipt.blockHash.hex(), True]
        response = self.assert_rpc_response(method="eth_getBlockByHash", params=params, raises=False)
        assert self.assert_result_object(response), AssertMessage.DOES_NOT_CONTAIN_RESULT

    @pytest.mark.parametrize(
        "quantity_tag,full_trx,raises",
        [
            (Tag.EARLIEST, True, False),
            (Tag.EARLIEST, False, True),
            (Tag.LATEST, True, False),
            (Tag.LATEST, False, True),
            (Tag.PENDING, True, False),
            (Tag.PENDING, False, True),
        ],
    )
    def test_eth_get_block_by_number_via_tags(self, quantity_tag: Tag, full_trx: bool, raises: bool):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        params = [quantity_tag.value, full_trx]
        response = self.assert_rpc_response(method="eth_getBlockByNumber", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.assert_result_object(response), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_eth_get_block_by_number_via_numbers(self):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        tx_receipt = self.process_transaction(self.sender_account, self.recipient_account, 10)
        response = self.assert_rpc_response(
            method="eth_getBlockByNumber", params=[tx_receipt.blockNumber, True], raises=False
        )
        assert self.assert_result_object(response), AssertMessage.DOES_NOT_CONTAIN_RESULT

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_block_number(self, params: tp.Union[str, bool], raises: bool):
        """Verify implemented rpc calls work work eth_blockNumber"""
        response = self.assert_rpc_response(method="eth_blockNumber", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.is_hex(response.result), f"Invalid response result {response.result}"

    @pytest.mark.parametrize(
        "params, raises", [(Tag.LATEST, False), (Tag.PENDING, False), (Tag.EARLIEST, False), (None, True)]
    )
    def test_eth_get_storage_at(self, params: tp.Union[Tag, bool], raises: bool):
        """Verify implemented rpc calls work eht_getStorageAt"""
        if params:
            params = [self.sender_account.address, hex(1), params.value]
        response = self.assert_rpc_response(method="eth_getStorageAt", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.is_hex(response.result), f"Invalid response: {response.result}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_mining(self, params, raises):
        """Verify implemented rpc calls work eth_mining"""
        self.assert_rpc_response(method="eth_mining", params=params, raises=raises)

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_syncing(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_syncing"""
        response = self.assert_rpc_response(method="eth_syncing", params=params, raises=raises)
        if hasattr(response, "result"):
            err_msg = f"Invalid response: {response.result}"
            if not isinstance(response.result, bool):
                assert all(isinstance(block, int) for block in response.result.values()), err_msg
            else:
                assert not response.result, err_msg

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_net_peer_count(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work net_peerCount"""
        response = self.assert_rpc_response(method="net_peerCount", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.is_hex(response.result), f"Invalid response: {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [("0x6865", False), ("param", True), (None, True)],
    )
    def test_web3_sha3(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work web3_sha3"""
        response = self.assert_rpc_response(method="web3_sha3", params=params, raises=raises)
        if hasattr(response, "result"):
            assert response.result.startswith("e5105")

    @pytest.mark.parametrize(
        "params, raises",
        [(32, False), (16, True), (None, True)],
    )
    def test_eth_get_block_transaction_count_by_hash(self, params: tp.Union[int, None], raises: bool):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByHash"""
        if params:
            params = input_data.gen_hash_of_block(params)
        response = self.assert_rpc_response(method="eth_getBlockTransactionCountByHash", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.is_hex(response.result), f"Invalid response: {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [(32, False), (Tag.EARLIEST.value, False), ("param", True), (None, True)],
    )
    def test_eth_get_block_transaction_count_by_number(self, params: tp.Union[int, str, None], raises: bool):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByNumber"""
        if isinstance(params, int):
            params = hex(params)
        response = self.assert_rpc_response(method="eth_getBlockTransactionCountByNumber", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.is_hex(response.result), f"Invalid response: {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [([32, 1], False), ([32, Tag.EARLIEST.value], False), ([16, 1], True), ([], True)],
    )
    def test_eth_get_transaction_by_block_hash_and_index(self, params: tp.List[tp.Union[int, str]], raises: bool):
        """Verify implemented rpc calls work eth_getTransactionByBlockHashAndIndex"""
        if params:
            params[0] = input_data.gen_hash_of_block(params[0])
        response = self.assert_rpc_response(
            method="eth_getTransactionByBlockHashAndIndex", params=params, raises=raises
        )
        if hasattr(response, "result"):
            assert response.result is None, f"Invalid response: {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [([32, 1], False), ([Tag.EARLIEST.value, 0], False), (["param", 1], True), ([], True)],
    )
    def test_eth_get_transaction_by_block_number_and_index(self, params: tp.List[tp.Union[int, str]], raises: bool):
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        if params:
            params = list(map(lambda i: hex(i) if isinstance(i, int) else i, params))
        response = self.assert_rpc_response(
            method="eth_getTransactionByBlockNumberAndIndex", params=params, raises=raises
        )
        if hasattr(response, "result"):
            assert response.result is None, f"Invalid response: {response.result}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_get_work(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_getWork"""
        response = self.assert_rpc_response(method="eth_getWork", params=params, raises=raises)
        if hasattr(response, "result"):
            assert len(response.result) >= 3, f"Invalid response result: {response.result}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_hash_rate(self, params: tp.Union[str, None], raises: bool):
        """Verify implemented rpc calls work eth_hashrate"""
        response = self.assert_rpc_response(method="eth_hashrate", params=params, raises=raises)
        if hasattr(response, "result"):
            assert self.is_hex(response.result), f"Invalid response result: {response.result}"

    @pytest.mark.parametrize("method", UNSUPPORTED_METHODS)
    def test_check_unsupported_methods(self, method: str):
        """Check that endpoint was not implemented"""
        with pytest.raises(AssertionError):
            payloads = getattr(RpcRequestFactory(), method)()
            response = self.json_rpc_client.do_call(payloads)
            err_message = getattr(response, "error", dict()).get("message")
            assert isinstance(response, request_models.JsonRpcResponse)
            assert err_message != f"method {method} is not supported"
