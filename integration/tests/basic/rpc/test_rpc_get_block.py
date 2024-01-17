import allure
import pytest

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import Tag
from utils.helpers import gen_hash_of_block
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify getBlock methods")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestRpcGetBlock:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash(self, full_trx: bool, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByHash"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, 10)
        params = [tx_receipt.blockHash.hex(), full_trx]
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=params)
        rpc_checks.assert_block_fields(response, full_trx, tx_receipt)

    @pytest.mark.parametrize(
        "hash_len, full_trx, msg",
        [(31, False, "bad block hash"), ("bad_hash", True, "bad block hash bad_hash")],
    )
    def test_eth_get_block_by_hash_with_incorrect_hash(self, hash_len, full_trx, msg, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        block_hash = gen_hash_of_block(hash_len) if isinstance(hash_len, int) else hash_len
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[block_hash, full_trx])
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == -32602
        assert msg in response["error"]["message"]

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash_with_not_existing_hash(self, full_trx, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        response = json_rpc_client.send_rpc(method="eth_getBlockByHash", params=[gen_hash_of_block(32), full_trx])
        assert response["result"] is None, "Result should be None"

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_number_via_numbers(self, full_trx, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, 10)
        response = json_rpc_client.send_rpc(
            method="eth_getBlockByNumber",
            params=[hex(tx_receipt.blockNumber), full_trx],
        )
        rpc_checks.assert_block_fields(response, full_trx, tx_receipt)

    def test_eth_get_block_by_number_with_incorrect_data(self, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = json_rpc_client.send_rpc(method="eth_getBlockByNumber", params=["bad_tag", True])
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == -32602
        assert "failed to parse block tag: bad_tag" in response["error"]["message"]

    @pytest.mark.parametrize(
        "number, full_trx",
        [
            (5, False),
            (31, False),
            (31, True),
            (32, True),
            (32, False),
        ],
    )
    def test_eth_get_block_by_number_with_not_exist_data(self, number, full_trx, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = json_rpc_client.send_rpc(method="eth_getBlockByNumber", params=[gen_hash_of_block(number), full_trx])
        assert response["result"] is None, "Result should be None"

    @pytest.mark.parametrize(
        "quantity_tag, full_trx",
        [
            (Tag.EARLIEST, True),
            (Tag.EARLIEST, False),
            (Tag.LATEST, True),
            (Tag.LATEST, False),
            (Tag.PENDING, True),
            (Tag.PENDING, False),
        ],
    )
    def test_eth_get_block_by_number_via_tags(self, quantity_tag: Tag, full_trx: bool, json_rpc_client):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.web3_client.send_neon(sender_account, recipient_account, 10)
        params = [quantity_tag.value, full_trx]
        response = json_rpc_client.send_rpc(method="eth_getBlockByNumber", params=params)
        rpc_checks.assert_block_fields(response, full_trx, None, quantity_tag == Tag.PENDING)
