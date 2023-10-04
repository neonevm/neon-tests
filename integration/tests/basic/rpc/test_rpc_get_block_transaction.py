import typing as tp

import allure
import pytest

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.errors import Error32000, Error32602
from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex, assert_equal_fields
from integration.tests.basic.rpc.test_rpc_base_calls import Tag
from utils.helpers import gen_hash_of_block


@allure.feature("JSON-RPC-GET-BLOCK-TRANSACTION validation")
@allure.story("Verify getBlockTransaction methods")
class TestRpcGetBlockTransaction(BaseMixin):
    @pytest.mark.parametrize("param", [32, 16, None])
    def test_eth_get_block_transaction_count_by_hash_negative(self, param: tp.Union[int, None]):
        response = self.proxy_api.send_rpc(
            method="eth_getBlockTransactionCountByHash",
            params=gen_hash_of_block(param) if param else param,
        )

        if param is pow(2, 5):
            assert "error" not in response
            assert response["result"] == "0x0", f"Invalid response: {response['result']}"
            return

        assert "error" in response, "error field not in response"
        assert "code" in response["error"]
        assert "message" in response["error"], "message field not in response"
        code = response["error"]["code"]
        message = response["error"]["message"]
        if param is None:
            assert code == Error32000.CODE, "wrong code"
            assert Error32000.MISSING_ARGUMENT in message, "wrong message"
            return

        assert code == Error32602.CODE, "wrong code"
        assert Error32602.BAD_BLOCK_HASH in message, "wrong message"

    def test_eth_get_block_transaction_count_by_hash(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, amount=0.001
        )
        response = self.proxy_api.send_rpc(
            method="eth_getBlockTransactionCountByHash",
            params=receipt["blockHash"].hex(),
        )

        assert "error" not in response
        assert int(response["result"], 16) != 0, "transaction count shouldn't be 0"

    @pytest.mark.parametrize("param", [32, Tag.EARLIEST.value, "param", None])
    def test_eth_get_block_transaction_count_by_number(
            self, param: tp.Union[int, str, None]
    ):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByNumber"""
        if isinstance(param, int):
            param = hex(param)
        response = self.proxy_api.send_rpc(
            method="eth_getBlockTransactionCountByNumber", params=param
        )
        if not param or param == "param":
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"
