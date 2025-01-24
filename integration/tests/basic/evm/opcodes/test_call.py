import os

import allure
import pytest
import web3

from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("Opcodes verifications")
@allure.story("Go-ethereum opCodes tests")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestOpcodeCall:
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

    @pytest.fixture(scope="class")
    def counter_with_log(self, web3_client, accounts):

        contract_address = os.environ.get("COUNTER_MAP_ADDRESS")
        if contract_address:
            contract = web3_client.get_deployed_contract(
                contract_address, contract_file="common/Counter", contract_name="CounterWithLogging"
            )
            print(f"Using CounterWithLogging deployed earlier at {contract_address}")
        else:
            contract, _ = web3_client.deploy_and_get_contract(
                "common/Counter", "0.8.10", contract_name="CounterWithLogging", account=accounts[0]
            )
            print(f"CounterWithLogging deployed at address: {contract.address}")
        return contract

    def test_state_change_call(self, counter_contract, contract_caller):

        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callInc(counter_contract.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callGet(counter_contract.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        count_from_log = contract_caller.events.LogCounterValue().process_receipt(resp)[0]["args"]["counter_value"]
        assert count_from_log == 1

    def test_count_not_changed_in_caller(self, counter_contract, contract_caller):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callInc(counter_contract.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.get().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        count_in_caller = contract_caller.events.LogCallerCountValue().process_receipt(resp)[0]["args"]["count"]
        assert count_in_caller == 0

    def test_sender_address_changed_to_contract_address(self, counter_with_log, contract_caller):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callIncWithSenderLog(counter_with_log.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        sender_in_counter = contract_caller.events.LogSenderInCounter().process_receipt(resp)[0]["args"][
            "sender_in_counter"]
        sender_in_caller = contract_caller.events.LogSenderInCaller().process_receipt(resp)[0]["args"][
            "sender_in_caller"]

        assert sender_in_counter != sender_in_caller
        assert sender_in_counter == resp["to"]

    def test_send_amount_to_callable_contract(self, counter_with_log, contract_caller):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account, amount=1)
        instruction_tx = contract_caller.functions.callIncWithSendValue(counter_with_log.address).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert resp["status"] == 1

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = counter_with_log.functions.getTotalReceived().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        total_received = counter_with_log.events.LogTotalReceived().process_receipt(resp)[0]["args"]["totalReceived"]
        assert total_received == 1

    def test_not_enough_gas_for_call(self, counter_contract, contract_caller):
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account, gas=2500)
        instruction_tx = contract_caller.functions.callInc(counter_contract.address).build_transaction(tx)
        with pytest.raises(ValueError):
            self.web3_client.send_transaction(sender_account, instruction_tx)
