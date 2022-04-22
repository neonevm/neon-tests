import typing as tp

import allure
import pytest

from integration.tests.basic.helpers.assert_message import AssertMessage
# <<<<<<< HEAD
# from integration.tests.basic.helpers.basic import WAITING_FOR_CONTRACT_SUPPORT, BasicTests
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.model.model import CallRequest, GetLogsRequest, TrxReceiptResponse, TrxResponse
from integration.tests.basic.model.tags import Tag
from integration.tests.basic.test_data.input_data import InputData
# =======
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.helpers.rpc_request_params_factory import RpcRequestParamsFactory
from integration.tests.basic.model import model as request_models
from integration.tests.basic.model.tags import Tag
from integration.tests.basic.test_data import input_data
# >>>>>>> develop

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

GET_LOGS_TEST_DATA = [
    (Tag.LATEST.value, Tag.LATEST.value),
    (Tag.EARLIEST.value, Tag.LATEST.value),
    (Tag.PENDING.value, Tag.LATEST.value),
    (Tag.LATEST.value, Tag.EARLIEST.value),
    (Tag.LATEST.value, Tag.PENDING.value),
]

# TODO: fix earliest and penging if possible
TAGS_TEST_DATA = [
    (Tag.EARLIEST, True),
    (Tag.EARLIEST, False),
    (Tag.LATEST, True),
    (Tag.LATEST, False),
    (Tag.PENDING, True),
    (Tag.PENDING, False),
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

# <<<<<<< HEAD
        # self.process_transaction(self.sender_account, self.recipient_account, InputData.SAMPLE_AMOUNT.value)
# =======
# >>>>>>> develop

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
        [({"to": None, "data": None}, False), ({}, True)],
    )
    def test_eth_call(self, params, raises):
        """Verify implemented rpc calls work eth_call"""
        if params:
            params.update({"to": self.recipient_account.address, "data": hex(pow(10, 14))})
        request_data = [request_models.CallRequest(**params), Tag.LATEST.value]
        response = self.assert_rpc_response("eth_call", params=request_data, raises=raises)
        if params:
            assert response.result == "0x", f"Invalid response result, `{response.result}`"

    @pytest.mark.parametrize(
        "params, raises",
        [({"from": None, "to": None, "value": hex(1)}, False), ({}, True)],
    )
    def test_eth_estimate_gas(self, params, raises):
        """Verify implemented rpc calls work eth_estimateGas"""
        if params:
            params.update({"from": self.sender_account.address, "to": self.recipient_account.address})
        response = self.assert_rpc_response("eth_estimateGas", params=params, raises=raises)
        if params:
            assert self.is_hex(response.result)

# <<<<<<< HEAD
#         # TOOD: variants
#         data = CallRequest(from_=self.sender_account.address, to=self.recipient_account.address, value=hex(1))
#         params = [data]
#         model = RpcRequestFactory.get_estimate_gas(params=params)
#         actual_result = self.json_rpc_client.do_call(model)
#         # actual_result = self.json_rpc_client.deserialize_response(response)

#         assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
#         # assert self.assert_no_error_object(
#         #     actual_result), AssertMessage.CONTAINS_ERROR
#         # assert self.assert_result_object(
#         #     actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

#     def test_rpc_call_eth_gasPrice(self):
# =======
    def test_eth_gas_price(self):
# >>>>>>> develop
        """Verify implemented rpc calls work eth_gasPrice"""
        payloads = RpcRequestFactory.get_gas_price(params=[])
        actual_result = self.json_rpc_client.do_call(payloads)

# <<<<<<< HEAD
#         assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
# =======
        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
# >>>>>>> develop
        assert self.assert_is_successful_response(actual_result), AssertMessage.WRONG_TYPE.value
        assert "0x" in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

    @pytest.mark.parametrize("from_block,to_block", GET_LOGS_TEST_DATA)
# <<<<<<< HEAD
#     def test_rpc_call_eth_getLogs_via_tags(self, from_block: Tag, to_block: Tag):
#         """Verify implemented rpc calls work eth_getLogs"""
#         # TODO: use contract instead of account
#         sender_account = self.create_account_with_balance()
#         params = [GetLogsRequest(from_block=from_block, to_block=to_block, address=sender_account.address)]
#         model = RpcRequestFactory.get_logs(params=params)
# =======
    def test_eth_get_logs_via_tags(self, from_block: Tag, to_block: Tag):
        """Verify implemented rpc calls work eth_getLogs"""
        # TODO: use contract instead of account
        sender_account = self.create_account_with_balance()
        params = [
            request_models.GetLogsRequest(from_block=from_block, to_block=to_block, address=sender_account.address)
        ]
        payloads = RpcRequestFactory.get_logs(params=params)
# >>>>>>> develop

        actual_result = self.json_rpc_client.do_call(payloads)

# <<<<<<< HEAD
#         assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
# =======
        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
# >>>>>>> develop
        assert self.assert_no_error_object(actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_eth_get_logs_via_numbers(self):
        """Verify implemented rpc calls work eth_getLogs"""
        # TODO: use contract instead of account
        sender_account = self.create_account_with_balance()
        # TOOD: variants
# <<<<<<< HEAD
#         params = [GetLogsRequest(from_block=1, to_block=Tag.LATEST.value, address=sender_account.address)]
#         model = RpcRequestFactory.get_logs(params=params)
# =======
        params = [
            request_models.GetLogsRequest(from_block=1, to_block=Tag.LATEST.value, address=sender_account.address)
        ]
        payloads = RpcRequestFactory.get_logs(params=params)
# >>>>>>> develop

        actual_result = self.json_rpc_client.do_call(payloads)

# <<<<<<< HEAD
#         assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
# =======
        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
# >>>>>>> develop
        assert self.assert_no_error_object(actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    @pytest.mark.only_stands
    def test_eth_get_balance(self):
        """Verify implemented rpc calls work eth_getBalance"""
        sender_account = self.create_account_with_balance()

        params = [sender_account.address, Tag.LATEST.value]
        payloads = RpcRequestFactory.get_balance(params=params)
        actual_result = self.json_rpc_client.do_call(payloads)

        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
        assert self.is_hex(actual_result.result), AssertMessage.WRONG_AMOUNT.value

    def test_eth_get_code(self):
        """Verify implemented rpc calls work eth_getCode"""
        # TODO: use contract instead of account?
        sender_account = self.create_account_with_balance()

        params = [sender_account.address, Tag.LATEST.value]
# <<<<<<< HEAD
#         model = RpcRequestFactory.get_code(params=params)
#         actual_result = self.json_rpc_client.do_call(model)
#         # actual_result = self.json_rpc_client.deserialize_response(response)

#         assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
#         assert self.assert_no_error_object(actual_result), AssertMessage.CONTAINS_ERROR
#         assert self.assert_result_object(actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

#     @pytest.mark.skip(WAITING_FOR_CONTRACT_SUPPORT)
#     def test_rpc_call_eht_getStorageAt(self):
#         """Verify implemented rpc calls work eht_getStorageAt"""
#         pass
# =======
        payloads = RpcRequestFactory.get_code(params=params)
        actual_result = self.json_rpc_client.do_call(payloads)

        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT
# >>>>>>> develop

    def test_web3_client_version(self):
        """Verify implemented rpc calls work web3_clientVersion"""
        payloads = RpcRequestFactory.get_web3_client_version(params=[])
        actual_result = self.json_rpc_client.do_call(payloads)

# <<<<<<< HEAD
#         assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
# =======
        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
# >>>>>>> develop
        assert self.assert_is_successful_response(actual_result), AssertMessage.WRONG_TYPE.value
        assert "Neon" in actual_result.result, "version does not contain 'Neon'"

    def test_net_version(self):
        """Verify implemented rpc calls work work net_version"""
        payloads = RpcRequestFactory.get_net_version(params=[])
        actual_result = self.json_rpc_client.do_call(payloads)

# <<<<<<< HEAD
#         assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
# =======
        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
# >>>>>>> develop
        assert self.assert_is_successful_response(actual_result), AssertMessage.WRONG_TYPE.value
        assert actual_result.result == str(
            self.web3_client._chain_id
        ), f"net version is not {self.web3_client._chain_id}"

# <<<<<<< HEAD


    def test_rpc_call_eth_get_transaction_count(self):
        """Verify implemented rpc calls work eth_getTransactionCount"""

        self.transfer_neon(self.sender_account, self.recipient_account, InputData.SAMPLE_AMOUNT.value)

        params = [self.sender_account.address, Tag.LATEST.value]
        model = RpcRequestFactory.get_trx_count(params=params)
        actual_result = self.json_rpc_client.do_call(model)
        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(actual_result), AssertMessage.WRONG_TYPE.value
        assert "0x" in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

    def test_rpc_call_eth_send_raw_transaction(self):
        """Verify implemented rpc calls work eth_sendRawTransaction"""

        # TODO: chain id
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))
        transaction = {
            "from": self.sender_account.address,
            "to": self.recipient_account.address,
            "value": self.web3_client.toWei(InputData.SAMPLE_AMOUNT.value, "ether"),
            "chainId": self.web3_client._chain_id,
            "gasPrice": self.web3_client.gas_price(),
            "gas": 0,
            "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)

        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]

        model = RpcRequestFactory.get_send_raw_trx(params=params)
        actual_result = self.json_rpc_client.do_call(model)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(actual_result), AssertMessage.WRONG_TYPE.value
        assert "0x" in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value
        self.assert_balance(self.recipient_account.address, recipient_balance + InputData.SAMPLE_AMOUNT.value)

    def test_rpc_call_eth_get_transaction_by_hash(self):
        """Verify implemented rpc calls work eth_getTransactionByHash"""

        tx_receipt = self.transfer_neon(self.sender_account, self.recipient_account, InputData.SAMPLE_AMOUNT.value)

        params = [tx_receipt.transactionHash.hex()]
        model = RpcRequestFactory.get_trx_by_hash(params=params)
        actual_result = self.json_rpc_client.do_call(model, TrxResponse)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_rpc_call_eth_get_transaction_receipt(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt"""

        tx_receipt = self.transfer_neon(self.sender_account, self.recipient_account, InputData.SAMPLE_AMOUNT.value)

        params = [tx_receipt.transactionHash.hex()]
        model = RpcRequestFactory.get_trx_receipt(params=params)
        actual_result = self.json_rpc_client.do_call(model, TrxReceiptResponse)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_eth_get_block_by_hash(self):
        """Verify implemented rpc calls work eth_getBlockByHash"""

        tx_receipt = self.transfer_neon(
            self.sender_account, self.recipient_account, input_data.InputData.SAMPLE_AMOUNT.value
        )

        params = [tx_receipt.blockHash.hex(), True]
        payloads = RpcRequestFactory.get_block_by_hash(params=params)

        actual_result = self.json_rpc_client.do_call(payloads, request_models.BlockResponse)

        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    @pytest.mark.parametrize("quantity_tag,full_trx", TAGS_TEST_DATA)
    def test_eth_get_block_by_umber_via_tags(self, quantity_tag: tp.Union[int, Tag], full_trx: bool):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        params = RpcRequestParamsFactory.get_block_by_number(quantity_tag, full_trx)
        payloads = RpcRequestFactory.get_block_by_number(params=params)

        actual_result = self.json_rpc_client.do_call(payloads, request_models.BlockResponse)
        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value

    def test_eth_get_block_by_number_via_numbers(self):
        """Verify implemented rpc calls work eth_getBlockByNumber"""

        tx_receipt = self.transfer_neon(
            self.sender_account, self.recipient_account, input_data.InputData.SAMPLE_AMOUNT.value
        )

        params = RpcRequestParamsFactory.get_block_by_number(tx_receipt.blockNumber, True)
        payloads = RpcRequestFactory.get_block_by_number(params=params)

        actual_result = self.json_rpc_client.do_call(payloads, request_models.BlockResponse)
        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_eth_block_number(self):
        """Verify implemented rpc calls work work eth_blockNumber"""
        payloads = RpcRequestFactory.get_block_number(params=[])
        actual_result = self.json_rpc_client.do_call(payloads)

        assert actual_result.id == payloads.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(actual_result), AssertMessage.WRONG_TYPE.value
        assert "0x" in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

    @pytest.mark.parametrize("params, raises", [(["latest"], False), ([], True)])
    def test_eth_get_storage_at(self, params, raises):
        """Verify implemented rpc calls work eht_getStorageAt"""
        if params:
            params = [self.sender_account.address, hex(1)] + params
        response = self.assert_rpc_response(method="eth_getStorageAt", params=params, raises=raises)
        if params:
            assert self.is_hex(response.result), f"Invalid response: {response.result}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_mining(self, params, raises):
        """Verify implemented rpc calls work eth_mining"""
        self.assert_rpc_response(method="eth_mining", params=params, raises=raises)

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_syncing(self, params, raises):
        """Verify implemented rpc calls work eth_syncing"""
        response = self.assert_rpc_response(method="eth_syncing", params=params, raises=raises)
        if not params:
            assert all(
                isinstance(block, int) for block in response.result.values()
            ), f"Invalid response: {response.result}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_net_peer_count(self, params, raises):
        """Verify implemented rpc calls work net_peerCount"""
        response = self.assert_rpc_response(method="net_peerCount", params=params, raises=raises)
        if not params:
            assert self.is_hex(response.result), f"Invalid response: {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [("0x6865", False), ("param", True), (None, True)],
    )
    def test_web3_sha3(self, params, raises):
        """Verify implemented rpc calls work web3_sha3"""
        response = self.assert_rpc_response(method="web3_sha3", params=params, raises=raises)
        if self.is_hex(params):
            assert response.result.startswith("e5105")

    @pytest.mark.parametrize(
        "params, raises",
        [(32, False), (16, True), (None, True)],
    )
    def test_eth_get_block_transaction_count_by_hash(self, params, raises):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByHash"""
        if params:
            params = input_data.gen_hash_of_block(params)
        response = self.assert_rpc_response(method="eth_getBlockTransactionCountByHash", params=params, raises=raises)
        if not raises:
            assert self.is_hex(response.result), f"Invalid response: {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [(32, False), ("earliest", False), ("param", True), (None, True)],
    )
    def test_eth_get_block_transaction_count_by_number(self, params, raises):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByNumber"""
        if params and isinstance(params, int):
            params = hex(params)
        response = self.assert_rpc_response(method="eth_getBlockTransactionCountByNumber", params=params, raises=raises)
        if not raises:
            assert self.is_hex(response.result), f"Invalid response: {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [([32, 1], False), ([32, "earliest"], False), ([16, 1], True), ([], True)],
    )
    def test_eth_get_transaction_by_block_hash_and_index(self, params, raises):
        """Verify implemented rpc calls work eth_getTransactionByBlockHashAndIndex"""
        if params:
            params[0] = input_data.gen_hash_of_block(params[0])
        response = self.assert_rpc_response(
            method="eth_getTransactionByBlockHashAndIndex", params=params, raises=raises
        )
        if not raises:
            assert response.result is None, f"Invalid response: {response.result}"

    @pytest.mark.parametrize(
        "params, raises",
        [([32, 1], False), (["earliest", 0], False), (["param", 1], True), ([], True)],
    )
    def test_eth_get_transaction_by_block_number_and_index(self, params, raises):
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        if params:
            params = list(map(lambda i: hex(i) if isinstance(i, int) else i, params))
        response = self.assert_rpc_response(
            method="eth_getTransactionByBlockNumberAndIndex", params=params, raises=raises
        )
        if not raises:
            assert response.result is None, f"Invalid response: {response.result}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_get_work(self, params, raises):
        """Verify implemented rpc calls work eth_getWork"""
        response = self.assert_rpc_response(method="eth_getWork", params=params, raises=raises)
        if not raises:
            assert len(response.result) >= 3, f"Invalid response result: {response.result}"

    @pytest.mark.parametrize("params, raises", [(None, False), ("param", True)])
    def test_eth_hash_rate(self, params, raises):
        """Verify implemented rpc calls work eth_hashrate"""
        response = self.assert_rpc_response(method="eth_hashrate", params=params, raises=raises)
        if not raises:
            assert self.is_hex(response.result), f"Invalid response result: {response.result}"

    @pytest.mark.parametrize("method", UNSUPPORTED_METHODS)
    def test_check_unsupported_methods(self, method):
        """Check that endpoint was not implemented"""
        with pytest.raises(AssertionError):
            payloads = getattr(RpcRequestFactory(), method)()
            response = self.json_rpc_client.do_call(payloads)
            err_message = getattr(response, "error", dict()).get("message")
            assert isinstance(response, request_models.JsonRpcResponse)
            assert err_message != f"method {method} is not supported"
# >>>>>>> develop
