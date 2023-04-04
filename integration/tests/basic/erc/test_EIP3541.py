import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("EIP Verifications")
@allure.story("EIP-3541: Reject new contract code starting with the 0xEF byte")
class TestRejectingContractsStartingWith0xEF(BaseMixin):

    @pytest.mark.parametrize("data",
                             ["0x60ef60005360016000f3", '0x60ef60005360026000f3',
                              '0x60ef60005360036000f3','0x60ef60005360206000f3'])
    def test_incorrect_calldata(self, data):
        transaction = self.create_contract_call_tx_object()
        transaction["gas"] = 1000000
        transaction["data"] = data
        transaction["chainId"] = self.web3_client._chain_id

        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        assert 'error' in response
        # TODO: check error message after fix NDEV-1539

    def test_correct_calldata(self):
        data = '0x60fe60005360016000f3'
        transaction = self.create_contract_call_tx_object()
        transaction["data"] = data
        transaction["chainId"] = self.web3_client._chain_id
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        assert 'error' not in response
        receipt = self.wait_transaction_accepted(response["result"])
        assert receipt["result"]["status"] == "0x1"
