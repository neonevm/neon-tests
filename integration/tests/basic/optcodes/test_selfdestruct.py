import random

import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("Optcodes verifications")
@allure.story("Self-destruction optcode")
class TestSelfDestructOptcode(BaseMixin):

    @pytest.fixture(scope="function")
    def destroyable_contract(self):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "SelfDestroyable", "0.8.10", self.sender_account)
        return contract

    @pytest.fixture(scope="function")
    def contract_caller(self, destroyable_contract):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "SelfDestroyable", "0.8.10", self.sender_account,
            contract_name="SelfDestroyableContractCaller",
            constructor_args=[destroyable_contract.address])
        return contract

    def deposit(self, destroyable_contract, sender, amount):
        tx = self.create_contract_call_tx_object(sender, amount=amount)
        instruction_tx = destroyable_contract.functions.deposit().buildTransaction(tx)
        self.web3_client.send_transaction(sender, instruction_tx)

    def destroy(self, destroyable_contract, sender, funds_recipient, amount=None):
        tx = self.create_contract_call_tx_object(sender, amount=amount)
        instruction_tx = destroyable_contract.functions.destroy(funds_recipient.address).buildTransaction(tx)
        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1

    def check_contract_code_is_empty(self, contract_address):
        response = self.proxy_api.send_rpc(
            "eth_getCode",
            params=[contract_address, "latest"]
        )
        assert response["result"] == "0x"

    def test_destroy(self, destroyable_contract):
        self.deposit(destroyable_contract, self.sender_account, 1)
        self.deposit(destroyable_contract, self.recipient_account, 1)

        balance_before = self.get_balance_from_wei(self.sender_account.address)
        self.destroy(destroyable_contract, self.sender_account, self.sender_account)

        balance_after = self.get_balance_from_wei(self.sender_account.address)

        assert 2 - balance_after - balance_before < 0.001

        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = destroyable_contract.functions.anyFunction().buildTransaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

        event_logs = destroyable_contract.events.FunctionCalled().processReceipt(receipt)
        assert event_logs == ()
        self.check_contract_code_is_empty(destroyable_contract.address)

    @pytest.mark.xfail(reason="SA-179")
    def test_destroy_contract_with_contract_address_as_target(self, destroyable_contract):
        self.deposit(destroyable_contract, self.recipient_account, 1)

        contract_balance_before = self.get_balance_from_wei(destroyable_contract.address)
        self.destroy(destroyable_contract, self.sender_account, destroyable_contract)

        contract_balance_after = self.get_balance_from_wei(destroyable_contract.address)
        assert contract_balance_after == contract_balance_before
        self.check_contract_code_is_empty(destroyable_contract.address)

    def test_destroy_contract_and_sent_neons_to_contract(self, destroyable_contract):
        self.deposit(destroyable_contract, self.sender_account, 1)
        self.destroy(destroyable_contract, self.sender_account, self.sender_account)

        amount = random.randint(1, 5)
        instruction_tx = self.create_tx_object(self.sender_account.address, destroyable_contract.address, amount=amount)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance_after = self.get_balance_from_wei(destroyable_contract.address)
        assert contract_balance_after == amount
        self.check_contract_code_is_empty(destroyable_contract.address)

    def test_destroy_contract_by_call_from_second_contract(self, destroyable_contract, contract_caller):
        self.deposit(destroyable_contract, self.sender_account, 2)
        recipient_balance_before = self.get_balance_from_wei(self.recipient_account.address)
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = contract_caller.functions.callDestroy(
            self.recipient_account.address).buildTransaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        recipient_balance_after = self.get_balance_from_wei(self.recipient_account.address)
        assert receipt["status"] == 1
        assert recipient_balance_after - recipient_balance_before == 2
        self.check_contract_code_is_empty(destroyable_contract.address)

    def test_destroy_contract_and_sent_neon_from_contract_in_one_trx(self, destroyable_contract, contract_caller):
        self.deposit(destroyable_contract, self.sender_account, 2)
        recipient_balance_before = self.get_balance_from_wei(self.recipient_account.address)
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = contract_caller.functions.callDestroyAndSendMoneyFromContract(
            self.recipient_account.address).buildTransaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        recipient_balance_after = self.get_balance_from_wei(self.recipient_account.address)
        assert receipt["status"] == 1
        assert recipient_balance_after - recipient_balance_before == 2
        self.check_contract_code_is_empty(destroyable_contract.address)

    def test_sent_neon_from_contract_and_destroy_contract_in_one_trx(self, destroyable_contract, contract_caller):
        self.deposit(destroyable_contract, self.sender_account, 2)

        recipient_balance_before = self.get_balance_from_wei(self.recipient_account.address)

        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = contract_caller.functions.sendMoneyFromContractAndCallDestroy(
            self.recipient_account.address).buildTransaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

        recipient_balance_after = self.get_balance_from_wei(self.recipient_account.address)

        assert self.get_balance_from_wei(destroyable_contract.address) == 0
        assert recipient_balance_after - recipient_balance_before == 2
        self.check_contract_code_is_empty(destroyable_contract.address)

    def test_destroy_contract_and_sent_neon_to_contract_in_one_trx(self, destroyable_contract):
        self.deposit(destroyable_contract, self.recipient_account, 1)

        balance_before = self.get_balance_from_wei(self.recipient_account.address)
        self.destroy(destroyable_contract, self.sender_account, self.recipient_account, amount=3)
        balance_after = self.get_balance_from_wei(self.recipient_account.address)
        assert balance_after - balance_before == 4
        self.check_contract_code_is_empty(destroyable_contract.address)

    def test_destroy_contract_2_times_in_one_trx(self, destroyable_contract, contract_caller):
        self.deposit(destroyable_contract, self.recipient_account, 1)
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = contract_caller.functions.callDestroyTwice(self.sender_account.address).buildTransaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        self.check_contract_code_is_empty(destroyable_contract.address)
