import allure
import pytest
import typing as tp
import web3

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.rpc.test_rpc_calls import Tag
from utils.consts import Unit


@allure.feature("JSON-RPC-GET_TRANSACTION validation")
@allure.story("Verify getTransaction methods")
class TestGetTransaction(BaseMixin):

    @staticmethod
    def validate_response(result, tx_receipt: tp.Union[web3.types.TxReceipt, None]):
        expected_hex_fields = [
            "blockHash",
            "blockNumber",
            "hash",
            "transactionIndex",
            "type",
            "from",
            "nonce",
            "gasPrice",
            "gas",
            "to",
            "value",
            "v",
            "s",
            "r",
        ]
        for field in expected_hex_fields:
            assert rpc_checks.is_hex(result[field])
        assert result["blockHash"] == tx_receipt.blockHash.hex()
        assert result["from"].upper() == tx_receipt["from"].upper()
        assert result["to"].upper() == tx_receipt["to"].upper()

    @pytest.mark.parametrize("valid_index", [True, False])
    def test_eth_get_transaction_by_block_number_and_index(self, valid_index: bool):
        amount = 10
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        tx_receipt = self.send_neon(
            self.sender_account, self.recipient_account, amount=amount
        )
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        transaction_index = (
            hex(tx_receipt.transactionIndex) if valid_index else hex(999)
        )
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex",
            params=[hex(tx_receipt.blockNumber), transaction_index],
        )
        if not valid_index:
            assert response["result"] is None, "Result should be None"
        else:
            assert "error" not in response
            result = response["result"]
            self.validate_response(result, tx_receipt)
            assert result["value"] == hex(self.web3_client.to_wei(amount, Unit.ETHER))

    @pytest.mark.parametrize("valid_index", [True, False])
    def test_eth_get_transaction_by_block_hash_and_index(self, valid_index: bool):
        """Verify implemented rpc calls work eth_getTransactionByBlockHashAndIndex"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        transaction_index = (
            hex(tx_receipt.transactionIndex) if valid_index else hex(999)
        )
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByBlockHashAndIndex",
            params=[tx_receipt.blockHash.hex(), transaction_index],
        )
        if not valid_index:
            assert response["result"] is None, "Result should be None"
        else:
            assert "error" not in response
            result = response["result"]
            self.validate_response(result, tx_receipt)

    @pytest.mark.parametrize("tag", [Tag.LATEST.value, Tag.EARLIEST.value, "param"])
    def test_eth_get_transaction_by_block_number_and_index_by_tag(self, tag: str):
        """Verify implemented rpc calls work eth_getTransactionByBlockNumberAndIndex"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByBlockNumberAndIndex",
            params=[tag, hex(tx_receipt.transactionIndex)],
        )
        if tag == "param":
            assert "error" in response, "Error not in response"
        else:
            assert "error" not in response
            result = response["result"]
            if result:
                expected_hex_fields = [
                    "blockHash",
                    "blockNumber",
                    "hash",
                    "transactionIndex",
                    "type",
                    "from",
                    "nonce",
                    "gasPrice",
                    "gas",
                    "value",
                    "v",
                    "s",
                    "r",
                ]
                for field in expected_hex_fields:
                    assert rpc_checks.is_hex(
                        result[field]
                    ), f"Field {field} must be hex but '{result[field]}'"
