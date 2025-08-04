import allure
import pytest

from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("Opcodes verifications")
@allure.story("Verify block timestamp and block number")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestBlockTimestampAndNumber:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_block_timestamp_call(self, block_timestamp_contract):
        contract, _ = block_timestamp_contract
        latest_block_timestamp = self.web3_client.eth.get_block("latest").timestamp
        assert contract.functions.getBlockTimestamp().call() >= latest_block_timestamp

    def test_block_timestamp_simple_trx(self, block_timestamp_contract):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.logTimestamp().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        tx_block_timestamp = self.web3_client.eth.get_block(receipt["blockHash"].hex()).timestamp

        event_logs = contract.events.Result().process_receipt(receipt)
        assert event_logs[0]["args"]["block_timestamp"] <= tx_block_timestamp

    def test_block_timestamp_iterative(self, block_timestamp_contract):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callIterativeTrx().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())

        tx_block_timestamp = self.web3_client.eth.get_block(receipt["blockHash"].hex()).timestamp
        event_logs = contract.events.Result().process_receipt(receipt)
        assert len(event_logs) == 1, "Event logs are not found"
        assert event_logs[0]["args"]["block_timestamp"] <= tx_block_timestamp

    def test_block_timestamp_constructor(self, block_timestamp_contract):
        contract, receipt = block_timestamp_contract
        tx_block_timestamp = self.web3_client.eth.get_block(receipt["blockHash"].hex()).timestamp
        assert contract.functions.accrualBlockTimestamp().call() <= tx_block_timestamp

    def test_block_timestamp_in_mapping(self, block_timestamp_contract, sol_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        v1 = 10
        v2 = 50
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.addDataToMapping(v1, v2, 30).build_transaction(tx)
        instruction_tx["gas"] *= 3  # to avoid out of gas
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())
        check_trx_is_success(self.web3_client, sol_client, receipt["transactionHash"].hex())
        tx_block_timestamp = self.web3_client.eth.get_block(receipt["blockHash"].hex()).timestamp
        event_logs = contract.events.DataAdded().process_receipt(receipt)
        added_timestamp = event_logs[0]["args"]["timestamp"]

        assert added_timestamp <= tx_block_timestamp
        assert contract.functions.getDataFromMapping(added_timestamp).call() == [v1, v2]

    def test_block_number_call(self, block_number_contract):
        contract, _ = block_number_contract
        current_block_number = self.web3_client.eth.get_block("latest").number

        assert contract.functions.getBlockNumber().call() >= current_block_number

    def test_block_number_simple_trx(self, block_number_contract):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.logBlockNumber().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        tx_block_number = self.web3_client.eth.get_block(receipt["blockHash"].hex()).number

        event_logs = contract.events.Result().process_receipt(receipt)
        assert event_logs[0]["args"]["block_number"] <= tx_block_number

    def test_block_number_iterative(self, block_number_contract):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callIterativeTrx().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())
        tx_block_number = self.web3_client.eth.get_block(receipt["blockHash"].hex()).number
        event_logs = contract.events.Result().process_receipt(receipt)

        assert event_logs[0]["args"]["block_number"] <= tx_block_number

    def test_block_number_constructor(self, block_number_contract):
        contract, receipt = block_number_contract
        tx_block_number = self.web3_client.eth.get_block(receipt["blockHash"].hex()).number

        assert contract.functions.accrualBlockNumber().call() <= tx_block_number

    def test_contract_deploys_contract_with_timestamp(self):
        deployer, receipt = self.web3_client.deploy_and_get_contract(
            "common/Block.sol", "0.8.10", self.accounts[0], contract_name="BlockTimestampDeployer"
        )
        tx_block_timestamp = self.web3_client.eth.get_block(receipt["blockHash"].hex()).timestamp
        addr = deployer.events.Log().process_receipt(receipt)[0]["args"]["addr"]
        contract = self.web3_client.get_deployed_contract(addr, "common/Block.sol", "BlockTimestamp")
        assert contract.functions.accrualBlockTimestamp().call() <= tx_block_timestamp

    @pytest.mark.skip(reason="https://neonlabs.atlassian.net/browse/NDEV-3701")
    def test_block_number_in_mapping(self, block_number_contract):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        v1 = 1
        v2 = 6
        instruction_tx = contract.functions.addDataToMapping(v1, v2, 30).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())
        assert receipt["status"] == 1
        event_logs = contract.events.DataAdded().process_receipt(receipt)
        assert len(event_logs) == 5, "Event logs are not found"
        block_number_added = event_logs[0]["args"]["number"]
        assert block_number_added <= receipt["blockNumber"]
        assert contract.functions.getDataFromMapping(block_number_added).call() == [v1, v2]
