import random
from typing import Type
import allure
from integration.tests.basic.model.json_rpc_response import JsonRpcResponse
import pytest
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


@allure.story("Basic: Json-RPC call tests")
class TestRpcCalls(BasicHelpers):
    # @pytest.mark.skip("not yet done")
    # @allure.step("test: verify implemented rpc calls work eth_getBlockByHash")
    # def test_rpc_call_eth_getBlockByHash(self):
    #     """Verify implemented rpc calls work eth_getBlockByHash"""
    #     model = RpcRequestFactory.get_block_by_hash(req_id=1,
    #                                                 params=RpcRequestParams())
    #     print(model)

    # @pytest.mark.skip("not yet done")
    # @allure.step("test: verify implemented rpc calls work eth_getBlockByNumber"
    #              )
    # def test_rpc_call_eth_getBlockByNumber(self):
    #     """Verify implemented rpc calls work eth_getBlockByNumber"""
    #     pass

    # @pytest.mark.skip("not yet done")
    # @allure.step("test: verify implemented rpc calls work eth_blockNumber")
    # def test_rpc_call_eth_blockNumber(self):
    #     """Verify implemented rpc calls work work eth_blockNumber"""
    #     pass

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

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_gasPrice")
    def test_rpc_call_eth_gasPrice(self):
        """Verify implemented rpc calls work eth_gasPrice"""
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_getLogs")
    def test_rpc_call_eth_getLogs(self):
        """Verify implemented rpc calls work eth_getLogs"""
        pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_getBalance")
    def test_rpc_call_eth_getBalance(self):
        """Verify implemented rpc calls work eth_getBalance"""
        pass

    # @pytest.mark.skip("not yet done")
    # @allure.step(
    #     "test: verify implemented rpc calls work eth_getTransactionCount")
    # def test_rpc_call_eth_getTransactionCount(self):
    #     """Verify implemented rpc calls work eth_getTransactionCount"""
    #     pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eth_getCode")
    def test_rpc_call_eth_getCode(self):
        """Verify implemented rpc calls work eth_getCode"""
        pass

    # @pytest.mark.skip("not yet done")
    # @allure.step(
    #     "test: verify implemented rpc calls work eth_sendRawTransaction")
    # def test_rpc_call_eth_sendRawTransaction(self):
    #     """Verify implemented rpc calls work eth_sendRawTransaction"""
    #     pass

    # @pytest.mark.skip("not yet done")
    # @allure.step(
    #     "test: verify implemented rpc calls work eth_getTransactionByHash")
    # def test_rpc_call_eth_getTransactionByHash(self):
    #     """Verify implemented rpc calls work eth_getTransactionByHash"""
    #     pass

    # @pytest.mark.skip("not yet done")
    # @allure.step(
    #     "test: verify implemented rpc calls work eth_getTransactionReceipt")
    # def test_rpc_call_eth_getTransactionReceipt(self):
    #     """Verify implemented rpc calls work eth_getTransactionReceipt"""
    #     pass

    @pytest.mark.skip("not yet done")
    @allure.step("test: verify implemented rpc calls work eht_getStorageAt")
    def test_rpc_call_eht_getStorageAt(self):
        """Verify implemented rpc calls work eht_getStorageAt"""
        pass

    @allure.step("test: verify implemented rpc calls work web3_clientVersion")
    def test_rpc_call_web3_clientVersion(self):
        """Verify implemented rpc calls work web3_clientVersion"""
        random_id = random.randint(0, 100)
        model = RpcRequestFactory.get_web3_client_version(req_id=random_id, params=[])

        #
        print(model)
        print(type(model))
        #

        response = self.jsonrpc_requester.request_json_rpc(model)

        #
        print(response)
        print(response.status_code)
        print(response.json())
        #

        result = self.jsonrpc_requester.deserialize(response.json())

        #
        print(type(result))
        print(result)
        #

        assert result.id == random_id
        assert 'Neon' in result.result

    @allure.step("test: verify implemented rpc calls work net_version")
    def test_rpc_call_net_version(self):
        """Verify implemented rpc calls work work net_version"""
        random_id = random.randint(0, 100)
        model = RpcRequestFactory.get_net_version(req_id=random_id, params=[])
        response = self.jsonrpc_requester.request_json_rpc(model)
        result = self.jsonrpc_requester.deserialize(response.json())

        #
        print(type(result))
        print(result)
        #

        assert result.id == random_id
        assert result.result == '111'
