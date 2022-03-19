import allure
import pytest
from typing import Type
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import WAITIING_FOR_CONTRACT_SUPPORT, BasicTests
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.model.model import CallRequest, GetLogsRequest
from integration.tests.basic.model.tags import Tag
from integration.tests.basic.test_data.input_data import InputData
'''
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
'''

GET_LOGS_TEST_DATA = [(Tag.LATEST.value, Tag.LATEST.value),
                      (Tag.EARLIEST.value, Tag.LATEST.value),
                      (Tag.PENDING.value, Tag.LATEST.value),
                      (Tag.LATEST.value, Tag.EARLIEST.value),
                      (Tag.LATEST.value, Tag.PENDING.value)]


@allure.story("Basic: Json-RPC call tests")
class TestRpcCalls(BasicTests):
    # TODO: implement numerous variants

    def test_rpc_call_eth_call(self, prepare_accounts):
        """Verify implemented rpc calls work eth_call"""

        self.transfer_neon(self.sender_account, self.recipient_account,
                           InputData.SAMPLE_AMOUNT.value)

        # TOOD: variants
        data = CallRequest(to=self.recipient_account.address)
        params = [data, Tag.LATEST.value]
        model = RpcRequestFactory.get_call(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        # assert self.assert_no_error_object(
        #     actual_result), AssertMessage.CONTAINS_ERROR
        # assert self.assert_result_object(
        #     actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    # TODO: implement numerous variants

    def test_rpc_call_eth_estimateGas(self, prepare_accounts):
        """Verify implemented rpc calls work eth_estimateGas"""

        # TOOD: variants
        data = CallRequest(from_=self.sender_account.address,
                           to=self.recipient_account.address,
                           value=hex(1))
        params = [data]
        model = RpcRequestFactory.get_estimate_gas(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        # assert self.assert_no_error_object(
        #     actual_result), AssertMessage.CONTAINS_ERROR
        # assert self.assert_result_object(
        #     actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_rpc_call_eth_gasPrice(self):
        """Verify implemented rpc calls work eth_gasPrice"""
        model = RpcRequestFactory.get_gas_price(params=[])
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(
            actual_result), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

    @pytest.mark.parametrize("from_block,to_block", GET_LOGS_TEST_DATA)
    def test_rpc_call_eth_getLogs_via_tags(self, from_block: Tag,
                                           to_block: Tag):
        """Verify implemented rpc calls work eth_getLogs"""
        # TODO: use contract instead of account
        sender_account = self.create_account_with_balance()
        params = [
            GetLogsRequest(from_block=from_block,
                           to_block=to_block,
                           address=sender_account.address)
        ]
        model = RpcRequestFactory.get_logs(params=params)

        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(
            actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(
            actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_rpc_call_eth_getLogs_via_numbers(self):
        """Verify implemented rpc calls work eth_getLogs"""
        # TODO: use contract instead of account
        sender_account = self.create_account_with_balance()
        # TOOD: variants
        params = [
            GetLogsRequest(from_block=1,
                           to_block=Tag.LATEST.value,
                           address=sender_account.address)
        ]
        model = RpcRequestFactory.get_logs(params=params)

        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(
            actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(
            actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    @pytest.mark.only_stands
    def test_rpc_call_eth_getBalance(self):
        """Verify implemented rpc calls work eth_getBalance"""
        sender_account = self.create_account_with_balance()

        params = [sender_account.address, Tag.LATEST.value]
        model = RpcRequestFactory.get_balance(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert actual_result.result == InputData.FIRST_AMOUNT_IN_RESPONSE.value, AssertMessage.WRONG_AMOUNT.value

    def test_rpc_call_eth_getCode(self):
        """Verify implemented rpc calls work eth_getCode"""
        # TODO: use contract instead of account?
        sender_account = self.create_account_with_balance()

        params = [sender_account.address, Tag.LATEST.value]
        model = RpcRequestFactory.get_code(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(
            actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(
            actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    @pytest.mark.skip(WAITIING_FOR_CONTRACT_SUPPORT)
    def test_rpc_call_eht_getStorageAt(self):
        """Verify implemented rpc calls work eht_getStorageAt"""
        pass

    def test_rpc_call_web3_clientVersion(self):
        """Verify implemented rpc calls work web3_clientVersion"""
        model = RpcRequestFactory.get_web3_client_version(params=[])
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(
            actual_result), AssertMessage.WRONG_TYPE.value
        assert 'Neon' in actual_result.result, "version does not contain 'Neon'"

    def test_rpc_call_net_version(self):
        """Verify implemented rpc calls work work net_version"""
        model = RpcRequestFactory.get_net_version(params=[])
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(
            actual_result), AssertMessage.WRONG_TYPE.value
        assert actual_result.result == str(
            self.web3_client._chain_id
        ), f"net version is not {self.web3_client._chain_id}"
