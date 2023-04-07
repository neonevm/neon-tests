import random

import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin

BAD_CALLDATA = ["0x60ef60005360016000f3", '0x60ef60005360026000f3',
                '0x60ef60005360036000f3', '0x60ef60005360206000f3']
GOOD_CALLDATA = ['0x60fe60005360016000f3']
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@allure.feature("EIP Verifications")
@allure.story("EIP-3541: Reject new contract code starting with the 0xEF byte")
class TestRejectingContractsStartingWith0xEF(BaseMixin):

    @pytest.mark.parametrize("data", BAD_CALLDATA)
    def test_sent_incorrect_calldata_via_trx(self, data):
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

    def test_sent_correct_calldata_via_trx(self):
        transaction = self.create_contract_call_tx_object()
        transaction["data"] = GOOD_CALLDATA[0]
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

    @pytest.fixture(scope="function")
    def eip3541_checker(self, web3_client):
        contract, _ = web3_client.deploy_and_get_contract(
            "EIP3541", "0.8.10", self.sender_account)
        return contract

    def test_sent_correct_calldata_via_create2(self, eip3541_checker):
        tx = self.create_contract_call_tx_object()
        seed = random.randint(1, 1000000)
        instruction_tx = eip3541_checker.functions.deploy(GOOD_CALLDATA[0], seed).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        event_logs = eip3541_checker.events.Deploy().process_receipt(receipt)
        assert event_logs[0].args.addr != ZERO_ADDRESS

    @pytest.mark.parametrize("data", BAD_CALLDATA)
    def test_sent_incorrect_calldata_via_create2(self, eip3541_checker, data):
        tx = self.create_contract_call_tx_object()
        seed = random.randint(1, 1000000)
        with pytest.raises(ValueError, match="unknown error"):
            eip3541_checker.functions.deploy(data, seed).build_transaction(tx)
        # TODO: check error message after fix NDEV-1539