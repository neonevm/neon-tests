from urllib import response
import allure
import pytest
from typing import Type
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.model.json_rpc_response import JsonRpcResponse
from integration.tests.basic.helpers.basic_helpers import FIRST_AMOUNT_IN_RESPONSE, FIRST_FAUCET_REQUEST_AMOUNT, BasicHelpers
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.model.json_rpc_request_parameters import JsonRpcRequestParams
from integration.tests.basic.model.tags import Tag
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


@allure.story("Basic: Json-RPC call tests")
class TestRpcCalls(BasicHelpers):
    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_call")
    def test_rpc_call_eth_call(self):
        """Verify implemented rpc calls work eth_call"""
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_estimateGas")
    def test_rpc_call_eth_estimateGas(self):
        """Verify implemented rpc calls work eth_estimateGas"""
        pass

    @allure.step("test: verify implemented rpc calls work eth_gasPrice")
    def test_rpc_call_eth_gasPrice(self):
        """Verify implemented rpc calls work eth_gasPrice"""
        model = RpcRequestFactory.get_gas_price(params=[])
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert isinstance(actual_result,
                          JsonRpcResponse), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_getLogs")
    def test_rpc_call_eth_getLogs(self):
        """Verify implemented rpc calls work eth_getLogs"""
        pass

    @allure.step("test: verify implemented rpc calls work eth_getBalance")
    def test_rpc_call_eth_getBalance(self):
        """Verify implemented rpc calls work eth_getBalance"""
        sender_account = self.create_account_with_balance(
            FIRST_FAUCET_REQUEST_AMOUNT)

        params = [sender_account.address, Tag.LATEST.value]
        model = RpcRequestFactory.get_balance(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert actual_result.result == FIRST_AMOUNT_IN_RESPONSE, AssertMessage.WRONG_AMOUNT.value

        # TODO: remove
        print(actual_result)
        #

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_getCode")
    def test_rpc_call_eth_getCode(self):
        """Verify implemented rpc calls work eth_getCode"""
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eht_getStorageAt")
    def test_rpc_call_eht_getStorageAt(self):
        """Verify implemented rpc calls work eht_getStorageAt"""
        pass

    @allure.step("test: verify implemented rpc calls work web3_clientVersion")
    def test_rpc_call_web3_clientVersion(self):
        """Verify implemented rpc calls work web3_clientVersion"""
        model = RpcRequestFactory.get_web3_client_version(params=[])
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert isinstance(actual_result,
                          JsonRpcResponse), AssertMessage.WRONG_TYPE.value
        assert 'Neon' in actual_result.result, "version does not contain 'Neon'"

    @allure.step("test: verify implemented rpc calls work net_version")
    def test_rpc_call_net_version(self):
        """Verify implemented rpc calls work work net_version"""
        model = RpcRequestFactory.get_net_version(params=[])
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert isinstance(actual_result,
                          JsonRpcResponse), AssertMessage.WRONG_TYPE.value
        assert actual_result.result == '111', "net version is not 111"
