import allure
import pytest
from integration.tests.basic.model.tags import Tag
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.model.json_rpc_response import JsonRpcResponse
from integration.tests.basic.helpers.helper_methods import FIRST_FAUCET_REQUEST_AMOUNT, GREAT_AMOUNT, BasicHelpers
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

SAMPLE_AMOUNT = 5


@allure.story("Basic: Json-RPC call tests - transactions")
class TestRpcCallsTransactions(BasicHelpers):
    @allure.step(
        "test: verify implemented rpc calls work eth_getTransactionCount")
    def test_rpc_call_eth_getTransactionCount(self):
        """Verify implemented rpc calls work eth_getTransactionCount"""
        sender_account = self.create_account_with_balance(GREAT_AMOUNT)
        recipient_account = self.create_account_with_balance(
            FIRST_FAUCET_REQUEST_AMOUNT)

        self.transfer_neon(sender_account, recipient_account, SAMPLE_AMOUNT)
        # ,
        # gas=0,  # 10_000,
        # gas_price=self.web3_client.gas_price()) # 0)  # 1_000_000_000)

        # self.assert_sender_amount(sender_account.address,
        #                           GREAT_AMOUNT - SAMPLE_AMOUNT)
        # self.assert_recipient_amount(recipient_account.address,
        #                              FIRST_FAUCET_REQUEST_AMOUNT + SAMPLE_AMOUNT)
        params = [sender_account.address, Tag.LATEST.value]  # TODO: enum
        model = RpcRequestFactory.get_trx_count(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert isinstance(actual_result,
                          JsonRpcResponse), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

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
