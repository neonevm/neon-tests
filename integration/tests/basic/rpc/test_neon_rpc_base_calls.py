import re

import allure
import pytest
from solders.instruction import Instruction, AccountMeta
from solders.pubkey import Pubkey
from web3.contract import Contract

from integration.tests.basic.helpers.errors import Error32602
from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex, assert_fields_are_specified_type
from utils.accounts import EthAccounts
from utils.consts import COUNTER_ID
from utils.helpers import serialize_instruction
from utils.types import TransactionType
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

    def test_neon_core_version(self, json_rpc_client):
        response = json_rpc_client.send_rpc(method="neon_coreVersion", params=[])
        pattern = r"Neon-Core-API/[vt]\d{1,2}.\d{1,2}.\d{1,2}.*"
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
    def test_neon_get_solana_transaction_by_neon_transaction_negative(self, params, json_rpc_client):
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

    def test_neon_estimate_gas_iterative_tx(
        self,
        block_timestamp_contract: Contract,
        default_cu_price: int | None,
    ):
        contract, _ = block_timestamp_contract
        sender = self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender)
        instruction_tx = contract.functions.callIterativeTrx().build_transaction(tx)

        neon_gas_estimate = self.web3_client.neon_estimate_gas(instruction_tx)["result"]

        assert neon_gas_estimate["exitCode"] == "succeed"
        assert neon_gas_estimate["externalSolanaCall"] is False
        assert neon_gas_estimate["gasAddressLookupTableUsed"] == 0
        assert neon_gas_estimate["gasFinishUsed"] == 0

        gas_used_sum = (
            neon_gas_estimate["gasAddressLookupTableUsed"]
            + neon_gas_estimate["gasExecutionUsed"]
            + neon_gas_estimate["gasFinishUsed"]
            + neon_gas_estimate["gasSolanaPriorityUsed"]
            + neon_gas_estimate["gasTransactionSizeUsed"]
        )
        assert gas_used_sum == neon_gas_estimate["gasUsed"]

        assert neon_gas_estimate["numEvmSteps"] == 46477
        assert neon_gas_estimate["numIterations"] == 95
        assert neon_gas_estimate["result"] == "0x"
        assert neon_gas_estimate["revertAfterSolanaCall"] is False
        assert neon_gas_estimate["revertBeforeSolanaCall"] is False
        assert len(neon_gas_estimate["solanaAccounts"]) == 2

        if default_cu_price is not None:
            assert neon_gas_estimate["solanaComputeUnitPrice"] == default_cu_price

    def test_neon_estimate_gas_external_solana_call(
        self,
        default_cu_price: int | None,
        counter_resource_address: bytes,
        call_solana_caller: Contract,
    ):
        iterations = 29
        sender = self.accounts[0]
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address, tx_type=TransactionType.EIP_1559)
        instruction_tx = call_solana_caller.functions.executeInIterativeMode(
            iterations, lamports, serialized
        ).build_transaction(tx)

        neon_gas_estimate = self.web3_client.neon_estimate_gas(instruction_tx)["result"]

        assert neon_gas_estimate["exitCode"] == "succeed"
        assert neon_gas_estimate["externalSolanaCall"] is True
        assert neon_gas_estimate["gasAddressLookupTableUsed"] == 60000
        assert neon_gas_estimate["gasFinishUsed"] == 0

        gas_used_sum = (
            neon_gas_estimate["gasAddressLookupTableUsed"]
            + neon_gas_estimate["gasExecutionUsed"]
            + neon_gas_estimate["gasFinishUsed"]
            + neon_gas_estimate["gasSolanaPriorityUsed"]
            + neon_gas_estimate["gasTransactionSizeUsed"]
        )
        assert gas_used_sum == neon_gas_estimate["gasUsed"]

        assert neon_gas_estimate["numEvmSteps"] == 2122
        assert neon_gas_estimate["numIterations"] == 7
        assert int(neon_gas_estimate["result"], 16) == iterations
        assert neon_gas_estimate["revertAfterSolanaCall"] is False
        assert neon_gas_estimate["revertBeforeSolanaCall"] is False
        assert len(neon_gas_estimate["solanaAccounts"]) == 33

        if default_cu_price is not None:
            assert neon_gas_estimate["solanaComputeUnitPrice"] == default_cu_price

    def test_neon_estimate_gas_invalid_params(self):
        sender = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender.address, estimate_gas=True)
        tx["data"] = "invalid"

        error = self.web3_client.neon_estimate_gas(tx)["error"]

        assert error["code"] == -32602
        assert error["message"] == "Invalid params"

        errors = error["data"]["errors"]
        assert len(errors) == 2
        assert "Value error, non-hexadecimal number" in errors[0], errors[0]
        assert "Value error, Wrong input type dict" in errors[1], errors[1]

    def test_neon_estimate_gas_failing_transaction(
        self,
        expected_error_checker: Contract,
        default_cu_price: int | None,
    ):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
        neon_gas_estimate = self.web3_client.neon_estimate_gas(instruction_tx)["result"]

        assert neon_gas_estimate["exitCode"] == "succeed"
        assert neon_gas_estimate["externalSolanaCall"] is False
        assert neon_gas_estimate["gasAddressLookupTableUsed"] == 0
        assert neon_gas_estimate["gasFinishUsed"] == 0

        gas_used_sum = (
            neon_gas_estimate["gasAddressLookupTableUsed"]
            + neon_gas_estimate["gasExecutionUsed"]
            + neon_gas_estimate["gasFinishUsed"]
            + neon_gas_estimate["gasSolanaPriorityUsed"]
            + neon_gas_estimate["gasTransactionSizeUsed"]
        )
        assert gas_used_sum == neon_gas_estimate["gasUsed"]

        assert neon_gas_estimate["numEvmSteps"] == 21832
        assert neon_gas_estimate["numIterations"] == 46
        assert neon_gas_estimate["result"] == "0x"
        assert neon_gas_estimate["revertAfterSolanaCall"] is False
        assert neon_gas_estimate["revertBeforeSolanaCall"] is False
        assert len(neon_gas_estimate["solanaAccounts"]) == 10

        if default_cu_price is not None:
            assert neon_gas_estimate["solanaComputeUnitPrice"] == default_cu_price

        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 0
