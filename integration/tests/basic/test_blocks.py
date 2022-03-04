import allure
import pytest
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.model.json_rpc_response import JsonRpcResponse
from integration.tests.basic.helpers.helper_methods import BasicHelpers
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.model.json_rpc_request_parameters import JsonRpcRequestParams
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


@allure.story("Basic: Json-RPC call tests - blocks")
class TestRpcCallsBlocks(BasicHelpers):
    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_getBlockByHash")
    def test_rpc_call_eth_getBlockByHash(self):
        """Verify implemented rpc calls work eth_getBlockByHash"""
        model = RpcRequestFactory.get_block_by_hash(
            req_id=1, params=JsonRpcRequestParams())

        # TODO: remove
        print(model)
        #

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_getBlockByNumber"
                 )
    def test_rpc_call_eth_getBlockByNumber(self):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        pass

    @allure.step("test: verify implemented rpc calls work eth_blockNumber")
    def test_rpc_call_eth_blockNumber(self):
        """Verify implemented rpc calls work work eth_blockNumber"""
        model = RpcRequestFactory.get_block_number(params=[])
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert isinstance(actual_result,
                          JsonRpcResponse), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value