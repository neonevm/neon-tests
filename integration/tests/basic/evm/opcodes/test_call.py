import allure
import pytest
import random
import string

from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("Opcodes verifications")
@allure.story("Go-ethereum opCodes call,staticcall, delegatecall")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestOpcodeCalls:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def contract_caller(self, web3_client, faucet, accounts):
        contract, _ = web3_client.deploy_and_get_contract(
            "opcodes/Call.sol",
            "0.8.0",
            accounts[0],
            contract_name="Caller",
        )
        return contract

    def test_staticcall(self, common_contract, contract_caller):
        sender_account = self.accounts[0]
        test_text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])

        tx = self.web3_client.make_raw_tx(sender_account)
        set_text_instruction_tx = common_contract.functions.setText(test_text).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, set_text_instruction_tx)

        text = contract_caller.functions.staticcallGetText(common_contract.address).call()
        assert text == test_text

    def test_staticcall_cannot_change_state(self, common_contract, contract_caller):
        sender_account = self.accounts[0]
        test_text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.staticcallSetText(
            common_contract.address, test_text
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        successfull = contract_caller.events.CallResult().process_receipt(resp)[0]["args"]["success"]
        assert not successfull

    def test_call_change_state(self, common_contract, contract_caller):
        """opcode call work with context of calling contract and change it's state and doesn't change own state"""
        sender_account = self.accounts[0]
        test_text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
        text_in_caller_before = contract_caller.functions.text().call()

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callSetText(common_contract.address, test_text).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        text_in_common = common_contract.functions.text().call()
        assert text_in_common == test_text

        text_in_caller_after = contract_caller.functions.text().call()
        assert text_in_caller_before == text_in_caller_after

    def test_call_change_sender_for_calling_contract(self, common_contract, contract_caller):
        sender_account = self.accounts[0]
        test_text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callSetTextReturnSenderAddr(
            common_contract.address, test_text
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        sender_in_calling_contract = contract_caller.events.LogSenderInCalledContract().process_receipt(resp)[0][
            "args"
        ]["sender_in_called_contract"]

        assert sender_in_calling_contract == contract_caller.address

    def test_call_send_amount_to_callable_contract(self, common_contract, contract_caller):
        sender_account = self.accounts[0]
        test_text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])

        tx = self.web3_client.make_raw_tx(sender_account, amount=10)
        instruction_tx = contract_caller.functions.callSetTextAndSendValue(
            common_contract.address, test_text
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        balance = self.web3_client.get_balance(common_contract.address)
        assert balance == 10

    def test_delegatecall_change_own_state(self, common_contract, contract_caller):
        sender_account = self.accounts[0]
        test_text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.delegateCallSetText(
            common_contract.address, test_text
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        text_in_calling_contract = contract_caller.functions.text().call()
        assert text_in_calling_contract == test_text

    def test_delegatecall_not_change_calling_contract_state(self, common_contract, contract_caller):
        sender_account = self.accounts[0]
        test_text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.delegateCallSetText(
            common_contract.address, test_text
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        text_in_called_contract = common_contract.functions.text().call()
        assert text_in_called_contract != test_text

    def test_delegatecall_save_original_sender_address(self, common_contract, contract_caller):
        sender_account = self.accounts[0]
        test_text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.delegatecallSetTextReturnSenderAddr(
            common_contract.address, test_text
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        sender_in_calling_contract = contract_caller.events.LogSenderInCalledContract().process_receipt(resp)[0][
            "args"
        ]["sender_in_called_contract"]

        assert sender_in_calling_contract == sender_account.address
