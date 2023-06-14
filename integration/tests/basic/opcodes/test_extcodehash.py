import allure
import pytest

from integration.tests.basic.helpers.basic import BaseMixin, AccountData
from eth_utils import keccak

from utils.consts import ZERO_HASH


@allure.feature("Opcodes verifications")
@allure.story("EIP-1052: EXTCODEHASH opcode")
class TestExtCodeHashOpcode(BaseMixin):
    @pytest.fixture(scope="class")
    def eip1052_checker(self, web3_client, faucet, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "EIPs/EIP1052_extcodehash", "0.8.10", class_account, contract_name="EIP1052Checker")
        return contract

    def test_extcodehash_for_contract_address(self, eip1052_checker):
        contract_hash = eip1052_checker.functions.getContractHash(eip1052_checker.address).call()
        assert contract_hash == keccak(self.web3_client.eth.get_code(eip1052_checker.address, "latest"))

    def test_extcodehash_with_send_tx_for_contract_address(self, eip1052_checker):
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(eip1052_checker.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        contract_hash = event_logs[0]['args']['hash']
        assert contract_hash == keccak(self.web3_client.eth.get_code(eip1052_checker.address, "latest"))

    def test_extcodehash_for_empty_account(self, eip1052_checker):
        # Check the EXTCODEHASH of the account without code is
        # c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
        # what is the keccack256 hash of empty data.
        contract_hash = eip1052_checker.functions.getContractHash(self.recipient_account.address).call()
        assert contract_hash.hex() == keccak(
            self.web3_client.eth.get_code(self.recipient_account.address, "latest")).hex()

    def test_extcodehash_with_send_tx_for_empty_account(self, eip1052_checker):
        # Check with send_tx the EXTCODEHASH of the account without code is
        # c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
        # what is the keccack256 hash of empty data.
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(self.recipient_account.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        contract_hash = event_logs[0]['args']['hash']
        assert contract_hash.hex() == keccak(
            self.web3_client.eth.get_code(self.recipient_account.address, "latest")).hex()

    def test_extcodehash_for_non_existing_account(self, eip1052_checker):
        non_existing_account = self.web3_client.to_checksum_address(self.create_invalid_account().address)
        contract_hash = eip1052_checker.functions.getContractHash(non_existing_account).call()
        assert contract_hash.hex() == ZERO_HASH

    def test_extcodehash_with_send_tx_for_non_existing_account(self, eip1052_checker):
        non_existing_account = self.web3_client.to_checksum_address(self.create_invalid_account().address)
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(non_existing_account).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        contract_hash = event_logs[0]['args']['hash']
        assert contract_hash.hex() == ZERO_HASH

    def test_extcodehash_for_destroyed_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of an account that selfdestructed in the current transaction.
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip1052_checker.functions.getHashForDestroyedContract().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        assert event_logs[1]['args']['hash'].hex() != ZERO_HASH
        assert event_logs[0]['args']['hash'].hex() == event_logs[1]['args']['hash'].hex()
        event_logs = eip1052_checker.events.DestroyedContract().process_receipt(receipt)
        destroyed_contract_address = event_logs[0]['args']['addr']
        assert eip1052_checker.functions.getContractHash(
            destroyed_contract_address).call().hex() == ZERO_HASH

    def test_extcodehash_with_send_tx_for_destroyed_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of an account that selfdestructed in the current transaction with send_tx.
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip1052_checker.functions.getHashForDestroyedContract().build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        event_logs = eip1052_checker.events.DestroyedContract().process_receipt(receipt)
        destroyed_contract_address = event_logs[0]['args']['addr']
        tx2 = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip1052_checker.functions\
            .getContractHashWithLog(destroyed_contract_address).build_transaction(tx2)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        assert event_logs[0]['args']['hash'].hex() == ZERO_HASH

    def test_extcodehash_for_reverted_destroyed_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of an account that selfdestructed and later the selfdestruct has been reverted.
        selfDestroyableContract, _ = self.web3_client.deploy_and_get_contract(
            "SelfDestroyable", "0.8.10", self.sender_account)
        destroyCaller, _ = self.web3_client.deploy_and_get_contract(
            "EIPs/EIP1052_extcodehash", "0.8.10", self.sender_account, contract_name="DestroyCaller")

        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip1052_checker.functions.getHashForDestroyedContractAfterRevert(
            selfDestroyableContract.address,
            destroyCaller.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        neon_logs = self.proxy_api.send_rpc(
            method="neon_getTransactionReceipt", params=[receipt["transactionHash"].hex()]
        )['result']['logs']
        data = [log['data'] for log in neon_logs if log['topics'] != []]
        assert data[0] != ZERO_HASH
        assert len(data) == 3
        assert all(x == data[0] for x in data)

    def test_extcodehash_for_precompiled_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of a precompiled contract.
        precompiled_acc = AccountData(address='0x0000000000000000000000000000000000000007')
        contract_hash = eip1052_checker.functions.getContractHash(precompiled_acc.address).call()
        assert contract_hash.hex() == ZERO_HASH

    def test_extcodehash_with_send_tx_for_precompiled_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of a precompiled contract with send_tx.
        precompiled_acc = AccountData(address='0x0000000000000000000000000000000000000007')
        tx = self.create_contract_call_tx_object(self.sender_account)
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(precompiled_acc.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        contract_hash = event_logs[0]['args']['hash']
        assert contract_hash.hex() == ZERO_HASH
