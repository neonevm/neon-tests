import random

import pytest

import allure

from utils.accounts import EthAccounts
from utils.models.result import EthGetBlockByHashResult
from utils.web3client import NeonChainWeb3Client


@pytest.fixture(scope="class")
def block_timestamp_contract(web3_client, accounts):
    block_timestamp_contract, receipt = web3_client.deploy_and_get_contract(
        "common/Block.sol", "0.8.10", accounts[0], contract_name="BlockTimestamp"
    )
    return block_timestamp_contract, receipt


@pytest.fixture(scope="class")
def block_number_contract(web3_client, accounts):
    block_number_contract, receipt = web3_client.deploy_and_get_contract(
        "common/Block.sol", "0.8.10", accounts[0], contract_name="BlockNumber"
    )
    return block_number_contract, receipt


@allure.feature("Opcodes verifications")
@allure.story("Verify block timestamp and block number")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestBlockTimestampAndNumber:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_block_timestamp_call(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        last_block = json_rpc_client.send_rpc("eth_blockNumber", [])["result"]
        current_timestamp = json_rpc_client.send_rpc("eth_getBlockByNumber", [last_block, False])["result"][
            "timestamp"
        ]
        assert hex(contract.functions.getBlockTimestamp().call()) >= current_timestamp

    def test_block_timestamp_simple_trx(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.logTimestamp().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        event_logs = contract.events.Result().process_receipt(receipt)
        assert hex(event_logs[0]["args"]["block_timestamp"]) <= tx_block_timestamp

    def test_block_timestamp_iterative(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callIterativeTrx().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())

        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        event_logs = contract.events.Result().process_receipt(receipt)
        assert len(event_logs) == 1, "Event logs are not found"
        assert hex(event_logs[0]["args"]["block_timestamp"]) <= tx_block_timestamp

    def test_block_timestamp_constructor(self, block_timestamp_contract, json_rpc_client):
        contract, receipt = block_timestamp_contract
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        assert hex(contract.functions.initial_block_timestamp().call()) <= tx_block_timestamp

    def test_block_timestamp_in_mapping(self, block_timestamp_contract, json_rpc_client):
        contract, _ = block_timestamp_contract
        sender_account = self.accounts[0]

        v1 = random.randint(1, 100)
        v2 = random.randint(1, 100)
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.addDataToMapping(v1, v2).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())
        assert receipt["status"] == 1
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        event_logs = contract.events.DataAdded().process_receipt(receipt)
        added_timestamp = event_logs[0]["args"]["timestamp"]

        assert added_timestamp <= int(tx_block_timestamp, 16)
        assert contract.functions.getDataFromMapping(added_timestamp).call() == [v1, v2]

    def test_block_number_call(self, block_number_contract, json_rpc_client):
        contract, _ = block_number_contract
        current_block_number = json_rpc_client.send_rpc(method="eth_blockNumber", params=[])["result"]
        assert hex(contract.functions.getBlockNumber().call()) >= current_block_number

    def test_block_number_simple_trx(self, block_number_contract, json_rpc_client):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.logBlockNumber().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_number = EthGetBlockByHashResult(**response).result.number

        event_logs = contract.events.Result().process_receipt(receipt)
        assert hex(event_logs[0]["args"]["block_number"]) <= tx_block_number

    def test_block_number_iterative(self, block_number_contract, json_rpc_client):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.callIterativeTrx().build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_number = EthGetBlockByHashResult(**response).result.number
        event_logs = contract.events.Result().process_receipt(receipt)

        assert hex(event_logs[0]["args"]["block_number"]) <= tx_block_number

    def test_block_number_constructor(self, block_number_contract, json_rpc_client):
        contract, receipt = block_number_contract
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_number = EthGetBlockByHashResult(**response).result.number

        assert hex(contract.functions.initial_block_number().call()) <= tx_block_number

    def test_contract_deploys_contract_with_timestamp(self, json_rpc_client):
        deployer, receipt = self.web3_client.deploy_and_get_contract(
            "common/Block.sol", "0.8.10", self.accounts[0], contract_name="BlockTimestampDeployer"
        )
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[receipt["blockHash"].hex(), False])
        tx_block_timestamp = EthGetBlockByHashResult(**response).result.timestamp

        addr = deployer.events.Log().process_receipt(receipt)[0]["args"]["addr"]
        contract = self.web3_client.get_deployed_contract(addr, "common/Block.sol", "BlockTimestamp")
        assert hex(contract.functions.initial_block_timestamp().call()) <= tx_block_timestamp

    def test_block_number_in_mapping(self, block_number_contract):
        contract, _ = block_number_contract
        sender_account = self.accounts[0]

        tx = self.web3_client.make_raw_tx(sender_account)
        v1 = random.randint(1, 100)
        v2 = random.randint(1, 100)
        instruction_tx = contract.functions.addDataToMapping(v1, v2).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert self.web3_client.is_trx_iterative(receipt["transactionHash"].hex())
        assert receipt["status"] == 1
        event_logs = contract.events.DataAdded().process_receipt(receipt)
        assert len(event_logs) == 5, "Event logs are not found"
        block_number_added = event_logs[0]["args"]["number"]
        assert block_number_added <= receipt["blockNumber"]
        assert contract.functions.getDataFromMapping(block_number_added).call() == [v1, v2]
