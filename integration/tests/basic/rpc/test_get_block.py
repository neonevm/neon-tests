import allure
import pytest

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import gen_hash_of_block


@allure.feature("JSON-RPC-GET-BLOCK validation")
@allure.story("Verify getBlock methods")
class TestGetBlock(BaseMixin):
    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash(self, full_trx: bool):
        """Verify implemented rpc calls work eth_getBlockByHash"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        params = [tx_receipt.blockHash.hex(), full_trx]
        response = self.proxy_api.send_rpc(method="eth_getBlockByHash", params=params)
        rpc_checks.assert_block_fields(response, full_trx, tx_receipt)

    @pytest.mark.parametrize(
        "hash_len, full_trx, msg",
        [(31, False, "bad block hash"), ("bad_hash", True, "bad block hash bad_hash")],
    )
    def test_eth_get_block_by_hash_with_incorrect_hash(self, hash_len, full_trx, msg):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        block_hash = (
            gen_hash_of_block(hash_len) if isinstance(hash_len, int) else hash_len
        )
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByHash", params=[block_hash, full_trx]
        )
        assert "error" in response, "Error not in response"
        assert response["error"]["code"] == -32602
        assert msg in response["error"]["message"]

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_hash_with_not_existing_hash(self, full_trx):
        """Verify implemented rpc calls work eth_getBlockByHash with incorrect hash"""
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByHash", params=[gen_hash_of_block(32), full_trx]
        )
        assert response["result"] is None, "Result should be None"

    @pytest.mark.parametrize("full_trx", [False, True])
    def test_eth_get_block_by_number_via_numbers(self, full_trx):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByNumber",
            params=[hex(tx_receipt.blockNumber), full_trx],
        )
        rpc_checks.assert_block_fields(response, full_trx, tx_receipt)

    def test_eth_get_block_by_number_with_incorrect_data(self):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByNumber", params=["bad_tag", True]
        )
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
    def test_eth_get_block_by_number_with_not_exist_data(self, number, full_trx):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        response = self.proxy_api.send_rpc(
            method="eth_getBlockByNumber", params=[gen_hash_of_block(number), full_trx]
        )
        assert response["result"] is None, "Result should be None"
