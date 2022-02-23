import allure
import pytest
from integration.tests.basic.helpers.helper_methods import BasicHelpers
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.model.rpc_request_parameters import RpcRequestParams
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


@allure.story("Basic: Json-RPC call tests - transactions")
class TestRpcCallsTransactions(BasicHelpers):
    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: verify implemented rpc calls work eth_getTransactionCount")
    def test_rpc_call_eth_getTransactionCount(self):
        """Verify implemented rpc calls work eth_getTransactionCount"""
        pass

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: verify implemented rpc calls work eth_sendRawTransaction")
    def test_rpc_call_eth_sendRawTransaction(self):
        """Verify implemented rpc calls work eth_sendRawTransaction"""
        pass

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: verify implemented rpc calls work eth_getTransactionByHash")
    def test_rpc_call_eth_getTransactionByHash(self):
        """Verify implemented rpc calls work eth_getTransactionByHash"""
        pass

    @pytest.mark.skip("not yet done")
    @allure.step(
        "test: verify implemented rpc calls work eth_getTransactionReceipt")
    def test_rpc_call_eth_getTransactionReceipt(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt"""
        pass
