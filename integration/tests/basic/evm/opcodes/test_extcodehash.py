import allure
import pytest
from eth_abi import abi
from web3.logs import DISCARD

from eth_utils import keccak

from integration.tests.basic.helpers.basic import AccountData
from utils.consts import ZERO_HASH
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client
from utils.helpers import create_invalid_address


@allure.feature("Opcodes verifications")
@allure.story("EIP-1052: EXTCODEHASH opcode")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestExtCodeHashOpcode:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.fixture(scope="class")
    def eip1052_checker(self, web3_client, faucet, class_account):
        contract, _ = web3_client.deploy_and_get_contract(
            "EIPs/EIP1052Extcodehash",
            "0.8.10",
            class_account,
            contract_name="EIP1052Checker",
        )
        return contract

    def test_extcodehash_for_contract_address(self, eip1052_checker):
        contract_hash = eip1052_checker.functions.getContractHash(eip1052_checker.address).call()
        assert contract_hash == keccak(self.web3_client.eth.get_code(eip1052_checker.address, "latest"))

    def test_extcodehash_with_send_tx_for_contract_address(self, eip1052_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(eip1052_checker.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        contract_hash = event_logs[0]["args"]["hash"]
        assert contract_hash == keccak(self.web3_client.eth.get_code(eip1052_checker.address, "latest"))

    def test_extcodehash_for_empty_account(self, eip1052_checker):
        # Check the EXTCODEHASH of the account without code is
        # c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
        # what is the keccack256 hash of empty data.
        recipient_account = self.accounts[1]
        contract_hash = eip1052_checker.functions.getContractHash(recipient_account.address).call()
        assert contract_hash.hex() == keccak(self.web3_client.eth.get_code(recipient_account.address, "latest")).hex()

    def test_extcodehash_with_send_tx_for_empty_account(self, eip1052_checker):
        # Check with send_tx the EXTCODEHASH of the account without code is
        # c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
        # what is the keccack256 hash of empty data.
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(recipient_account.address).build_transaction(
            tx
        )
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        contract_hash = event_logs[0]["args"]["hash"]
        assert contract_hash.hex() == keccak(self.web3_client.eth.get_code(recipient_account.address, "latest")).hex()

    def test_extcodehash_for_non_existing_account(self, eip1052_checker):
        non_existing_account = self.web3_client.to_checksum_address(create_invalid_address())
        contract_hash = eip1052_checker.functions.getContractHash(non_existing_account).call()
        assert contract_hash.hex() == ZERO_HASH

    def test_extcodehash_with_send_tx_for_non_existing_account(self, eip1052_checker):
        non_existing_account = self.web3_client.to_checksum_address(create_invalid_address())
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(non_existing_account).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        contract_hash = event_logs[0]["args"]["hash"]
        assert contract_hash.hex() == ZERO_HASH

    def test_extcodehash_for_destroyed_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of an account that selfdestructed in the current transaction.
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = eip1052_checker.functions.getHashForDestroyedContract().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt, errors=DISCARD)
        assert event_logs[1]["args"]["hash"].hex() != ZERO_HASH
        assert event_logs[0]["args"]["hash"].hex() == event_logs[1]["args"]["hash"].hex()
        event_logs = eip1052_checker.events.DestroyedContract().process_receipt(receipt, errors=DISCARD)
        destroyed_contract_address = event_logs[0]["args"]["addr"]
        assert eip1052_checker.functions.getContractHash(destroyed_contract_address).call().hex() == ZERO_HASH

    def test_extcodehash_with_send_tx_for_destroyed_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of an account that selfdestructed in the current transaction with send_tx.
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = eip1052_checker.functions.getHashForDestroyedContract().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_logs = eip1052_checker.events.DestroyedContract().process_receipt(receipt, errors=DISCARD)
        destroyed_contract_address = event_logs[0]["args"]["addr"]
        tx2 = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(destroyed_contract_address).build_transaction(
            tx2
        )
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt, errors=DISCARD)
        assert event_logs[0]["args"]["hash"].hex() == ZERO_HASH

    def test_extcodehash_for_reverted_destroyed_contract(self, eip1052_checker, json_rpc_client):
        # Check the EXTCODEHASH of an account that selfdestructed and later the selfdestruct has been reverted.
        sender_account = self.accounts[0]
        selfDestroyableContract, _ = self.web3_client.deploy_and_get_contract(
            "opcodes/SelfDestroyable", "0.8.10", sender_account
        )
        destroyCaller, _ = self.web3_client.deploy_and_get_contract(
            "EIPs/EIP1052Extcodehash",
            "0.8.10",
            sender_account,
            contract_name="DestroyCaller",
        )

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = eip1052_checker.functions.getHashForDestroyedContractAfterRevert(
            selfDestroyableContract.address, destroyCaller.address
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        neon_logs = json_rpc_client.send_rpc(
            method="neon_getTransactionReceipt",
            params=[receipt["transactionHash"].hex(), "neon"],
        )["result"]["logs"]
        data = [log["data"] for log in neon_logs if log["neonEventType"] == "Log"]
        # TODO fix checking
        # assert data[0] != ZERO_HASH
        # assert len(data) == 3
        # assert all(x == data[0] for x in data)

    @pytest.mark.only_stands
    def test_extcodehash_for_precompiled_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of a precompiled contract.
        precompiled_acc = AccountData(address="0xFf00000000000000000000000000000000000004")
        contract_hash = eip1052_checker.functions.getContractHash(precompiled_acc.address).call()
        assert contract_hash.hex() == ZERO_HASH

    @pytest.mark.only_stands
    def test_extcodehash_with_send_tx_for_precompiled_contract(self, eip1052_checker):
        # Check the EXTCODEHASH of a precompiled contract with send_tx.
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        precompiled_acc = AccountData(address="0xFf00000000000000000000000000000000000004")
        instruction_tx = eip1052_checker.functions.getContractHashWithLog(precompiled_acc.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt)
        contract_hash = event_logs[0]["args"]["hash"]
        assert contract_hash.hex() == ZERO_HASH

    @pytest.mark.only_stands
    def test_extcodehash_for_new_account_with_changed_balance(self, eip1052_checker, common_contract):
        # Check the EXTCODEHASH of a new account after sent some funds to it in one transaction
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, amount=1)
        new_acc = self.web3_client.create_account()
        instruction_tx = eip1052_checker.functions.TransferAndGetHash(new_acc.address).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        event_logs = eip1052_checker.events.ReceivedHash().process_receipt(receipt, errors=DISCARD)

        assert event_logs[0]["args"]["hash"].hex() == ZERO_HASH
        assert event_logs[1]["args"]["hash"] == keccak(self.web3_client.eth.get_code(new_acc.address, "latest"))

    @pytest.mark.only_stands
    def test_extcodehash_for_new_account_with_changed_nonce(self, eip1052_checker, json_rpc_client):
        new_account = self.web3_client.create_account()

        calldata = keccak(text="getContractHashWithLog(address)")[:4] + abi.encode(
            ["address"],
            [new_account.address],
        )
        params = [
            {"from": new_account.address, "nonce": 1, "to": eip1052_checker.address, "data": calldata.hex()},
            "latest",
        ]

        response = json_rpc_client.send_rpc("eth_call", params=params)
        assert response["result"][2:] == keccak(self.web3_client.eth.get_code(new_account.address, "latest")).hex()
