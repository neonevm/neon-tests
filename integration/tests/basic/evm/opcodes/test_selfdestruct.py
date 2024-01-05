import random

import allure
import pytest

from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("Opcodes verifications")
@allure.story("Self-destruction opcode")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestSelfDestructOpcode:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="function")
    def destroyable_contract(self, accounts):
        sender_account = self.accounts[0]
        contract, _ = self.web3_client.deploy_and_get_contract("opcodes/SelfDestroyable", "0.8.10", sender_account)
        return contract

    @pytest.fixture(scope="function")
    def contract_caller(self, destroyable_contract, accounts):
        sender_account = self.accounts[0]
        contract, _ = self.web3_client.deploy_and_get_contract(
            "opcodes/SelfDestroyable",
            "0.8.10",
            sender_account,
            contract_name="SelfDestroyableContractCaller",
            constructor_args=[destroyable_contract.address],
        )
        return contract

    def deposit(self, destroyable_contract, sender, amount):
        tx = self.web3_client.make_raw_tx(sender, amount=amount)
        instruction_tx = destroyable_contract.functions.deposit().build_transaction(tx)
        self.web3_client.send_transaction(sender, instruction_tx)

    def destroy(self, destroyable_contract, sender, funds_recipient, amount=None):
        tx = self.web3_client.make_raw_tx(sender, amount=amount)
        instruction_tx = destroyable_contract.functions.destroy(funds_recipient.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1

    def check_contract_code_is_not_empty(self, contract_address, proxy_api):
        response = proxy_api.send_rpc("eth_getCode", params=[contract_address, "latest"])
        assert response["result"] != "0x"

    def test_destroy(self, destroyable_contract, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(destroyable_contract, sender_account, 1)
        self.deposit(destroyable_contract, recipient_account, 1)

        balance_before_user1 = self.web3_client.get_balance(sender_account)
        balance_before_user2 = self.web3_client.get_balance(recipient_account)
        self.destroy(destroyable_contract, sender_account, sender_account)

        balance_after_user1 = self.web3_client.get_balance(sender_account)
        balance_after_user2 = self.web3_client.get_balance(recipient_account)

        assert 2 - balance_after_user1 - balance_before_user1 < 0.001
        assert balance_after_user2 == balance_before_user2
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = destroyable_contract.functions.anyFunction().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        self.check_contract_code_is_not_empty(destroyable_contract.address, json_rpc_client)

    def test_destroy_contract_with_contract_address_as_target(self, destroyable_contract, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(destroyable_contract, recipient_account, 1)

        contract_balance_before = self.web3_client.get_balance(destroyable_contract)
        self.destroy(destroyable_contract, sender_account, destroyable_contract)

        contract_balance_after = self.web3_client.get_balance(destroyable_contract.address)
        assert contract_balance_after == contract_balance_before
        self.check_contract_code_is_not_empty(destroyable_contract.address, json_rpc_client)

    def test_destroy_contract_and_sent_neons_to_contract(self, destroyable_contract, json_rpc_client):
        sender_account = self.accounts[0]
        self.deposit(destroyable_contract, sender_account, 1)
        self.destroy(destroyable_contract, sender_account, sender_account)

        amount = random.randint(1, 5)
        instruction_tx = self.web3_client.make_raw_tx(
            sender_account, to=destroyable_contract.address, amount=amount, estimate_gas=True
        )
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance_after = self.web3_client.get_balance(destroyable_contract.address)
        assert contract_balance_after == amount
        self.check_contract_code_is_not_empty(destroyable_contract.address, json_rpc_client)

    def test_destroy_contract_by_call_from_second_contract(
        self, destroyable_contract, contract_caller, json_rpc_client
    ):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(destroyable_contract, sender_account, 2)
        recipient_balance_before = self.web3_client.get_balance(recipient_account.address)
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callDestroy(recipient_account.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        recipient_balance_after = self.web3_client.get_balance(recipient_account.address)
        assert receipt["status"] == 1
        assert recipient_balance_after - recipient_balance_before == 2
        self.check_contract_code_is_not_empty(destroyable_contract.address, json_rpc_client)

    def test_destroy_contract_and_sent_neon_from_contract_in_one_trx(
        self, destroyable_contract, contract_caller, json_rpc_client
    ):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(destroyable_contract, sender_account, 2)
        recipient_balance_before = self.web3_client.get_balance(recipient_account.address)
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callDestroyAndSendMoneyFromContract(
            recipient_account.address
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        recipient_balance_after = self.web3_client.get_balance(recipient_account.address)
        assert receipt["status"] == 1
        assert recipient_balance_after - recipient_balance_before == 2
        self.check_contract_code_is_not_empty(destroyable_contract.address, json_rpc_client)

    def test_sent_neon_from_contract_and_destroy_contract_in_one_trx(
        self, destroyable_contract, contract_caller, json_rpc_client
    ):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(destroyable_contract, sender_account, 2)

        recipient_balance_before = self.web3_client.get_balance(recipient_account.address)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.sendMoneyFromContractAndCallDestroy(
            recipient_account.address
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

        recipient_balance_after = self.web3_client.get_balance(recipient_account.address)

        assert self.web3_client.get_balance(destroyable_contract.address) == 0
        assert recipient_balance_after - recipient_balance_before == 2
        self.check_contract_code_is_not_empty(destroyable_contract.address, json_rpc_client)

    def test_destroy_contract_and_sent_neon_to_contract_in_one_trx(self, destroyable_contract, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(destroyable_contract, recipient_account, 1)

        balance_before = self.web3_client.get_balance(recipient_account.address)
        self.destroy(destroyable_contract, sender_account, recipient_account, amount=3)
        balance_after = self.web3_client.get_balance(recipient_account.address)
        assert balance_after - balance_before == 4
        self.check_contract_code_is_not_empty(destroyable_contract.address, json_rpc_client)

    def test_destroy_contract_2_times_in_one_trx(self, destroyable_contract, contract_caller, json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(destroyable_contract, recipient_account, 1)
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract_caller.functions.callDestroyTwice(sender_account.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        self.check_contract_code_is_not_empty(destroyable_contract.address, json_rpc_client)

    def test_destroy_contract_via_delegatecall(self, destroyable_contract, contract_caller, json_rpc_client):
        # contract_caller should be destroyed instead of destroyable_contract
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account)
        instr = contract_caller.functions.callDestroyViaDelegateCall(sender_account.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instr)

        assert receipt["status"] == 1
        assert self.web3_client.eth.get_code(destroyable_contract.address) != "0x"
        self.check_contract_code_is_not_empty(contract_caller.address, json_rpc_client)

    def test_destroy_contract_via_delegatecall_and_create_new_contract(
        self, destroyable_contract, contract_caller, json_rpc_client
    ):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account)
        instr = contract_caller.functions.callDestroyViaDelegateCallAndCreateNewContract(
            sender_account.address
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instr)

        assert receipt["status"] == 1
        assert self.web3_client.eth.get_code(destroyable_contract.address) != "0x"
        self.check_contract_code_is_not_empty(contract_caller.address, json_rpc_client)
