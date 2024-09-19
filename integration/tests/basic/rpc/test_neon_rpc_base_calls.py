import re

import allure
import pytest

from integration.tests.basic.helpers.errors import Error32602
from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex, assert_fields_are_specified_type
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC proxy calls work")
@pytest.mark.usefixtures("accounts", "web3_client")
@pytest.mark.neon_only
class TestNeonRPCBaseCalls:
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    @pytest.mark.parametrize(
        "params, error_code, error_message",
        [
            ([{"from": "0x0"}], Error32602.CODE, Error32602.BAD_FROM_ADDRESS),
        ],
    )
    def test_neon_gas_price_negative(self, params, error_code, error_message, json_rpc_client):
        """Verify implemented rpc calls work with neon_gasPrice, negative cases"""
        response = json_rpc_client.send_rpc("neon_gasPrice", params=params)
        assert "error" in response, "error field not in response"
        assert "code" in response["error"]
        assert "message" in response["error"], "message field not in response"

    def test_neon_gas_price(self, json_rpc_client):
        """Verify implemented rpc calls work neon_gasPrice"""
        sender_account = self.accounts[0]
        params = [{"from": sender_account.address, "nonce": self.web3_client.get_nonce(sender_account)}]
        response = json_rpc_client.send_rpc("neon_gasPrice", params=params)
        assert "error" not in response
        assert "result" in response
        result = response["result"]
        assert_fields_are_hex(
            result,
            [
                "gasPrice",
                "suggestedGasPrice",
                "minAcceptableGasPrice",
                "minExecutableGasPrice",
                "minWoChainIDAcceptableGasPrice",
                "chainTokenPriceUsd",
                "tokenPriceUsd",
                "operatorFee",
            ],
        )
        assert_fields_are_specified_type(bool, result, ["isConstGasPrice"])
        gas_price = result["gasPrice"]
        assert int(gas_price, 16) > 100000000, f"gas price should be greater 100000000, got {int(gas_price, 16)}"

    def test_neon_cli_version(self, json_rpc_client):
        response = json_rpc_client.send_rpc(method="neon_cli_version", params=[])
        pattern = r"Neon-cli/[vt]\d{1,2}.\d{1,2}.\d{1,2}.*"
        assert re.match(
            pattern, response["result"]
        ), f"Version format is not correct. Pattern: {pattern}; Response: {response}"

    def test_neon_get_solana_transaction_by_neon_transaction(self, event_caller_contract, json_rpc_client, sol_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
        params = [tx_receipt["transactionHash"].hex()]
        response = json_rpc_client.send_rpc(method="neon_getSolanaTransactionByNeonTransaction", params=params)
        assert "result" in response
        sol_tx = response["result"][0]
        assert sol_client.wait_transaction(sol_tx) is not None

    @pytest.mark.proxy_version("v1.12.0")
    def test_neon_get_solana_transaction_by_neon_transaction_list_of_tx(self, json_rpc_client, sol_client):
        sender_account = self.accounts[0]
        _, tx_receipt = self.web3_client.deploy_and_get_contract("common/EventCaller", "0.8.12", sender_account)
        params = [tx_receipt["transactionHash"].hex()]
        response = json_rpc_client.send_rpc(method="neon_getSolanaTransactionByNeonTransaction", params=params)
        assert "result" in response
        result = response["result"]
        assert len(result) == 5
        for tx in result:
            assert sol_client.wait_transaction(tx) is not None

    @pytest.mark.parametrize(
        "params",
        [
            ([0x0],),
            ([None],),
            (["0x0"],),
            ([],),
        ],
    )
    def test_neon_get_solana_transaction_by_neon_transaction_negative(
        self, params, json_rpc_client
    ):
        response = json_rpc_client.send_rpc(method="neon_getSolanaTransactionByNeonTransaction", params=params)
        assert "error" in response, "error field not in response"
        assert "code" in response["error"]
        assert "message" in response["error"], "message field not in response"
        assert Error32602.CODE == response["error"]["code"]
        assert Error32602.INVALID_TRANSACTIONID == response["error"]["message"]

    def test_neon_get_solana_transaction_by_neon_transaction_non_existent_tx(self, json_rpc_client):
        response = json_rpc_client.send_rpc(
            method="neon_getSolanaTransactionByNeonTransaction",
            params="0x044852b2a670ade5407e78fb2863c51de9fcb96542a07186fe3aeda6bb8a116d",
        )
        assert "error" not in response
        assert len(response["result"]) == 0, "expected empty result for non existent transaction request"

    def test_neon_get_native_token_list(self, pytestconfig, json_rpc_client):
        response = json_rpc_client.send_rpc(method="neon_getNativeTokenList")
        assert "error" not in response
        assert len(response["result"]) == len(pytestconfig.environment.network_ids), \
            f"Wrong list length. Initial -> {pytestconfig.environment.network_ids}. Actual -> {response['result']}"
        # Check that all fields are present
        for item in response["result"]:
            assert "tokenChainId" in item
            assert item["tokenChainId"] is not None
            assert "tokenMint" in item
            assert item["tokenMint"] is not None
            assert "tokenName" in item
            assert item["tokenName"] is not None
        
        # Check that NEON token is present in the list
        tokens = [item["tokenName"] for item in response["result"]]
        assert "NEON" in tokens, f"NEON token is not in the list: {tokens}"
        for item in response["result"]:
            if item["tokenName"] == "NEON":
                assert item["tokenMint"] == pytestconfig.environment.spl_neon_mint
                assert item["tokenChainId"] == hex(pytestconfig.environment.network_ids["neon"])
