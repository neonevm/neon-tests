import allure
import pytest
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BasicTests
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.test_data.input_data import InputData


@allure.story("Basic: Json-RPC call tests - transactions validation")
class TestRpcCallsTransactions(BasicTests):
    def test_generate_bad_sign(self, prepare_accounts):
        """Generate bad sign (when v, r, s over allowed size)"""

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
        self.assert_balance(
            self.recipient_account.address,
            InputData.FAUCET_1ST_REQUEST_AMOUNT.value +
            InputData.SAMPLE_AMOUNT.value)
