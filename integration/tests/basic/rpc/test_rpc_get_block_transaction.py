import typing as tp

import allure
import pytest

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.rpc.test_rpc_base_calls import Tag
from utils.helpers import gen_hash_of_block


@allure.feature("JSON-RPC-GET-BLOCK-TRANSACTION validation")
@allure.story("Verify getBlockTransaction methods")
class TestRpcGetBlockTransaction(BaseMixin):
    @pytest.mark.parametrize("param", [128, 32, 16, None])
    def test_eth_get_block_transaction_count_by_hash(self, param: tp.Union[int, None]):
        """Verify implemented rpc calls work eth_getBlockTransactionCountByHash"""
        response = self.proxy_api.send_rpc(
            method="eth_getBlockTransactionCountByHash",
            params=gen_hash_of_block(param) if param else param,
        )
        if not param or param != pow(2, 5):
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"

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
