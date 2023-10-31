import random

import allure
import pytest
import web3.exceptions

from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import ZERO_ADDRESS

BAD_CALLDATA = [
    "0x60ef60005360016000f3",
    "0x60ef60005360026000f3",
    "0x60ef60005360036000f3",
    "0x60ef60005360206000f3",
]
GOOD_CALLDATA = ["0x60fe60005360016000f3"]

EIP_3541_ERROR_MESSAGE = (
    BAD_START_CONTRACT_CODE_EIP354
) = r"execution reverted: New contract code starting with the 0xEF byte \(EIP-3541\), contract = (\w+)"


@allure.feature("EIP Verifications")
@allure.story("EIP-3541: Reject new contract code starting with the 0xEF byte")
class TestRejectingContractsStartingWith0xEF(BaseMixin):
    @pytest.mark.parametrize("data", BAD_CALLDATA)
    def test_sent_incorrect_calldata_via_trx(self, data):
        transaction = self.create_contract_call_tx_object()
        transaction["data"] = data
        transaction["chainId"] = self.web3_client.eth.chain_id

        with pytest.raises(
            web3.exceptions.ContractLogicError, match=EIP_3541_ERROR_MESSAGE
        ):
            self.web3_client.send_transaction(self.sender_account, transaction)

    def test_sent_correct_calldata_via_trx(self):
        transaction = self.create_contract_call_tx_object()
        transaction["data"] = GOOD_CALLDATA[0]
        transaction["chainId"] = self.web3_client.eth.chain_id
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)

        receipt = self.web3_client.eth.wait_for_transaction_receipt(tx)
        assert receipt["status"] == 1

    @pytest.fixture(scope="function")
    def eip3541_checker(self, web3_client):
        contract, _ = web3_client.deploy_and_get_contract(
            "EIPs/EIP3541Reject0xEF",
            "0.8.10",
            self.sender_account,
            contract_name="EIP3541",
        )
        return contract

    def test_sent_correct_calldata_via_create2(self, eip3541_checker):
        tx = self.create_contract_call_tx_object()
        seed = random.randint(1, 1000000)
        instruction_tx = eip3541_checker.functions.deploy(
            GOOD_CALLDATA[0], seed
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        event_logs = eip3541_checker.events.Deploy().process_receipt(receipt)
        assert event_logs[0].args.addr != ZERO_ADDRESS

    @pytest.mark.parametrize("data", BAD_CALLDATA)
    def test_sent_incorrect_calldata_via_create2(self, eip3541_checker, data):
        tx = self.create_contract_call_tx_object()
        seed = random.randint(1, 1000000)
        instruction_tx = eip3541_checker.functions.deploy(data, seed).build_transaction(
            tx
        )
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        event_logs = eip3541_checker.events.Deploy().process_receipt(receipt)
        assert event_logs[0].args.addr == ZERO_ADDRESS
