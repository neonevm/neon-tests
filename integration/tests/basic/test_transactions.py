import allure
import pytest
from integration.tests.basic.helpers.basic import BasicTests
from integration.tests.basic.model.model import TrxReceiptResponse, TrxResponse
from integration.tests.basic.model.tags import Tag
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
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


@allure.story("Basic: Json-RPC call tests - transactions")
class TestRpcCallsTransactions(BasicTests):
    def test_rpc_call_eth_getTransactionCount(self, prepare_accounts):
        """Verify implemented rpc calls work eth_getTransactionCount"""

        self.transfer_neon(self.sender_account, self.recipient_account,
                           InputData.SAMPLE_AMOUNT.value)

        params = [self.sender_account.address, Tag.LATEST.value]
        model = RpcRequestFactory.get_trx_count(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(
            actual_result), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

    def test_rpc_call_eth_sendRawTransaction(self, prepare_accounts):
        """Verify implemented rpc calls work eth_sendRawTransaction"""

        # TODO: chain id
        transaction = {
            "from":
            self.sender_account.address,
            "to":
            self.recipient_account.address,
            "value":
            self.web3_client.toWei(InputData.SAMPLE_AMOUNT.value, "ether"),
            "chainId":
            self.web3_client._chain_id,
            "gasPrice":
            self.web3_client.gas_price(),
            "gas":
            0,
            "nonce":
            self.web3_client.eth.get_transaction_count(
                self.sender_account.address),
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)

        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]

        model = RpcRequestFactory.get_send_raw_trx(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(
            actual_result), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

        # TODO: calculate sender's amount
        # self.assert_balance(
        #     self.sender_account.address,
        #     InputData.FAUCET_1ST_REQUEST_AMOUNT.value -
        #     InputData.SAMPLE_AMOUNT.value -
        #     self.calculate_trx_gas(tx_receipt=actual_result.result))
        self.assert_balance(
            self.recipient_account.address,
            InputData.FAUCET_1ST_REQUEST_AMOUNT.value +
            InputData.SAMPLE_AMOUNT.value)

    def test_rpc_call_eth_getTransactionByHash(self, prepare_accounts):
        """Verify implemented rpc calls work eth_getTransactionByHash"""

        tx_receipt = self.transfer_neon(self.sender_account,
                                        self.recipient_account,
                                        InputData.SAMPLE_AMOUNT.value)

        params = [tx_receipt.transactionHash.hex()]
        model = RpcRequestFactory.get_trx_by_hash(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(
            response, TrxResponse)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(
            actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(
            actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_rpc_call_eth_getTransactionReceipt(self, prepare_accounts):
        """Verify implemented rpc calls work eth_getTransactionReceipt"""

        tx_receipt = self.transfer_neon(self.sender_account,
                                        self.recipient_account,
                                        InputData.SAMPLE_AMOUNT.value)

        params = [tx_receipt.transactionHash.hex()]
        model = RpcRequestFactory.get_trx_receipt(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(
            response, TrxReceiptResponse)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(
            actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(
            actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

        result_object = self.jsonrpc_requester.deserialize_response