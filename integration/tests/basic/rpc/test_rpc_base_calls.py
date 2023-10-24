import re
import time
import typing as tp

import allure
import pytest
import web3
from eth_utils import keccak

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin, Tag
from integration.tests.basic.helpers.errors import Error32000, Error32602
from integration.tests.basic.helpers.rpc_checks import is_hex, hex_str_consists_not_only_of_zeros
from integration.tests.helpers.basic import cryptohex
from utils.helpers import gen_hash_of_block


GET_LOGS_TEST_DATA = [
    (Tag.LATEST.value, Tag.LATEST.value),
    (Tag.EARLIEST.value, Tag.LATEST.value),
    (Tag.PENDING.value, Tag.LATEST.value),
    (Tag.LATEST.value, Tag.EARLIEST.value),
    (Tag.LATEST.value, Tag.PENDING.value),
]

UNSUPPORTED_METHODS = [
    "eth_accounts",
    "eth_coinbase",
    "eth_compileLLL",
    "eth_compileSerpent",
    "eth_compileSolidity",
    "eth_getCompilers",
    "eth_getFilterChanges",
    "eth_getStorage",
    "eth_getUncleByBlockHashAndIndex",
    "eth_getUncleByBlockNumberAndIndex",
    "eth_getUncleCountByBlockHash",
    "eth_getUncleCountByBlockNumber",
    "eth_newBlockFilter",
    "eth_newFilter",
    "eth_newPendingTransactionFilter",
    "eth_protocolVersion",
    "eth_sendTransaction",
    "eth_sign",
    "eth_signTransaction",
    "eth_submitHashrate",
    "eth_submitWork",
    "eth_uninstallFilter",
    "shh_addToGroup",
    "shh_getFilterChanges",
    "shh_getMessages",
    "shh_hasIdentity",
    "shh_newFilter",
    "shh_newGroup",
    "shh_newIdentity",
    "shh_post",
    "shh_uninstallFilter",
    "shh_version",
    "eth_getWork",
    "eth_hashrate"
]


def get_event_signatures(abi: tp.List[tp.Dict]) -> tp.List[str]:
    """Get topics as keccak256 from abi Events"""
    topics = []
    for event in filter(lambda item: item["type"] == "event", abi):
        input_types = ",".join(i["type"] for i in event["inputs"])
        signature = f"{event['name']}({input_types})"
        topics.append(f"0x{keccak(signature.encode()).hex()}")
    return topics


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC proxy calls work")
class TestRpcBaseCalls(BaseMixin):
    def test_eth_call_without_params(self):
        """Verify implemented rpc calls work eth_call without params"""
        response = self.proxy_api.send_rpc("eth_call")
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("tag", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST])
    def test_eth_call(self, tag):
        """Verify implemented rpc calls work eth_call"""
        params = [
            {"to": self.recipient_account.address, "data": hex(pow(10, 14))},
            tag.value,
        ]

        response = self.proxy_api.send_rpc("eth_call", params=params)
        assert "error" not in response
        assert (
                response["result"] == "0x"
        ), f"Invalid response result, `{response['result']}`"

    def test_eth_gas_price(self):
        """Verify implemented rpc calls work eth_gasPrice"""
        response = self.proxy_api.send_rpc("eth_gasPrice")
        assert "error" not in response
        assert "result" in response
        result = response["result"]
        assert rpc_checks.is_hex(result), f"Invalid current gas price `{result}` in wei"
        assert int(result, 16) > 100000000, f"gas price should be greater 100000000, got {int(result, 16)}"

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    @pytest.mark.only_stands
    def test_eth_get_balance(self, param: tp.Union[Tag, None]):
        """Verify implemented rpc calls work eth_getBalance"""
        response = self.proxy_api.send_rpc(
            "eth_getBalance",
            params=[self.sender_account.address, param.value if param else param],
        )
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), AssertMessage.WRONG_AMOUNT.value

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    def test_eth_get_code(self, event_caller_contract, param: tp.Union[Tag, None]):
        """Verify implemented rpc calls work eth_getCode"""
        response = self.proxy_api.send_rpc(
            "eth_getCode",
            params=[event_caller_contract.address, param.value] if param else param,
        )
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert "result" in response
        result = response["result"]
        assert is_hex(result), f"Invalid compiled byte code in response {result} at a given contract address"
        assert result.startswith("0x")
        assert len(result) == 6678
        assert hex_str_consists_not_only_of_zeros(result), "Response result hex str should not consist only of zeros"

    def test_eth_get_code_sender_address(self):
        response = self.proxy_api.send_rpc(
            "eth_getCode",
            params=[self.sender_account.address, Tag.LATEST.value],
        )
        assert "error" not in response
        assert (
                response["result"] == "0x"
        ), f"Invalid response {response['result']} at a given contract address"

    def test_eth_get_code_wrong_address(self):
        """Verify implemented rpc calls work eth_getCode"""
        response = self.proxy_api.send_rpc(
            "eth_getCode",
            params=[cryptohex("12345"), Tag.LATEST.value],
        )
        assert "error" in response
        assert "message" in response["error"]
        assert "bad address" in response["error"]["message"]

    def test_web3_client_version(self):
        """Verify implemented rpc calls work web3_clientVersion"""
        response = self.proxy_api.send_rpc("web3_clientVersion")
        assert "error" not in response
        assert "Neon" in response["result"], "Invalid response result"

    def test_net_version(self):
        """Verify implemented rpc calls work work net_version"""
        response = self.proxy_api.send_rpc("net_version")
        assert "error" not in response
        assert int(response["result"]) == self.web3_client._chain_id, \
            f"Invalid response result {response['result']}"

    def test_eth_send_raw_transaction(self):
        """Verify implemented rpc calls work eth_sendRawTransaction"""
        transaction = self.create_tx_object(amount=1)

        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", params=signed_tx.rawTransaction.hex()
        )
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result {response['result']}"

    def test_eth_sendRawTransaction_max_size(self):
        """Validate max size for transaction, 127 KB"""
        size = 127 * 1024
        transaction = self.create_tx_object(amount=1)

        transaction["data"] = gen_hash_of_block(size)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", params=signed_tx.rawTransaction.hex()
        )
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result {response['result']}"

    def test_eth_sendRawTransaction_max_contract_size(self):
        """Validate max size for contract, 24 KB"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/BigMemoryValue", "0.8.12",
            contract_name="ValueOf24K", account=self.sender_account
        )
        assert rpc_checks.is_hex(contract.address)

    def test_eth_block_number(self):
        """Verify implemented rpc calls work work eth_blockNumber"""
        response = self.proxy_api.send_rpc(method="eth_blockNumber")
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result {response['result']}"

    def test_eth_block_number_next_block_different(self):
        response = self.proxy_api.send_rpc(method="eth_blockNumber")
        time.sleep(1)
        response2 = self.proxy_api.send_rpc(method="eth_blockNumber")

        assert "error" not in response and response2
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result {response['result']}"
        assert rpc_checks.is_hex(response2["result"]), f"Invalid response result {response2['result']}"
        assert response['result'] != response2['result']

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, Tag.SAFE, Tag.FINALIZED, None])
    def test_eth_get_storage_at(self, event_caller_contract, param: tp.Union[Tag, None]):
        """Verify implemented rpc calls work eht_getStorageAt"""
        response = self.proxy_api.send_rpc(
            method="eth_getStorageAt",
            params=[event_caller_contract.address, hex(1), param.value]
            if param
            else param,
        )
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        result = response["result"]
        assert rpc_checks.is_hex(result), f"Invalid response: {result}"
        assert int(result, 16) == 52193458690378020725790142635571483517433973554952025871423338986830750023688

    def test_eth_get_storage_at_eq_val(self):
        """Verify implemented rpc calls work eht_getStorageAt and equal values"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/StorageSoliditySource", "0.8.12",
            contract_name="StorageMultipleVars", account=self.sender_account
        )
        responses = [
            self.proxy_api.send_rpc("eth_getStorageAt", [contract.address, hex(0), Tag.LATEST.value]),
            self.proxy_api.send_rpc("eth_getStorageAt", [contract.address, hex(1), Tag.EARLIEST.value]),
            self.proxy_api.send_rpc("eth_getStorageAt", [contract.address, hex(2), Tag.LATEST.value])
        ]

        for i in range(len(responses)):
            assert "error" not in responses[i]
            assert "result" in responses[i]

        assert "test" in web3.Web3.to_text(responses[0]["result"]), "wrong variable value"
        assert int(responses[1]["result"], 16) == 0, "wrong storage value"
        assert int(responses[2]["result"], 16) == 0, "wrong storage value"

        new_data = "new"
        instruction_tx = contract.functions.setData(new_data).build_transaction(self.make_contract_tx_object())
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        response = (
            self.proxy_api.send_rpc("eth_getStorageAt", [contract.address, hex(0), Tag.LATEST.value]))
        assert "error" not in response
        assert "result" in response
        assert new_data in web3.Web3.to_text(response["result"]), "wrong variable value"

    def test_eth_mining(self):
        """Verify implemented rpc calls work eth_mining"""
        response = self.proxy_api.send_rpc(method="eth_mining")
        assert "error" not in response
        assert isinstance(response["result"], bool), f"Invalid response: {response['result']}"

    def test_eth_syncing(self):
        """Verify implemented rpc calls work eth_syncing"""
        response = self.proxy_api.send_rpc(method="eth_syncing")
        if hasattr(response, "result"):
            err_msg = f"Invalid response: {response.result}"
            if not isinstance(response["result"], bool):
                assert all(
                    isinstance(block, int) for block in response["result"].values()
                ), err_msg
            else:
                assert not response.result, err_msg

    def test_net_peer_count(self):
        """Verify implemented rpc calls work net_peerCount"""
        response = self.proxy_api.send_rpc(method="net_peerCount")
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("param", ["0x6865", "param", None, True])
    def test_web3_sha3(self, param: tp.Union[str, None]):
        """Verify implemented rpc calls work web3_sha3"""
        response = self.proxy_api.send_rpc(method="web3_sha3", params=param)
        if isinstance(param, str) and param.startswith("0"):
            assert "error" not in response
            assert response["result"][2:].startswith("e5105")
        else:
            assert "error" in response, "Error not in response"
            assert "code" in response["error"], "no error code in response"
            assert "message" in response["error"]
            code = response["error"]["code"]
            message = response["error"]["message"]
            if param is None:
                assert code == Error32000.CODE, "wrong code"
                assert Error32000.MISSING_ARGUMENT in message, "wrong error message"
            else:
                assert code == Error32602.CODE, "wrong code"
                assert Error32602.NOT_HEX in message, "wrong error message"

    @pytest.mark.parametrize("method", UNSUPPORTED_METHODS)
    def test_check_unsupported_methods(self, method: str):
        """Check that endpoint was not implemented"""
        response = self.proxy_api.send_rpc(method)
        assert "error" in response
        assert "message" in response["error"]
        assert (
                response["error"]["message"]
                == f"the method {method} does not exist/is not available"
        ), response

    def test_get_evm_params(self):
        response = self.proxy_api.send_rpc(method="neon_getEvmParams", params=[])

        expected_fields = [
            "NEON_GAS_LIMIT_MULTIPLIER_NO_CHAINID",
            "NEON_SEED_VERSION",
            "NEON_EVM_STEPS_LAST_ITERATION_MAX",
            "NEON_PAYMENT_TO_DEPOSIT",
            "NEON_COMPUTE_UNITS",
            "NEON_REQUEST_UNITS_ADDITIONAL_FEE",
            "NEON_PKG_VERSION",
            "NEON_HEAP_FRAME",
            "NEON_ACCOUNT_SEED_VERSION",
            "NEON_TOKEN_MINT",
            "NEON_TREASURY_POOL_SEED",
            "NEON_STORAGE_ENTRIES_IN_CONTRACT_ACCOUNT",
            "NEON_EVM_STEPS_MIN",
            "NEON_PAYMENT_TO_TREASURE",
            "NEON_OPERATOR_PRIORITY_SLOTS",
            "NEON_STATUS_NAME",
            "NEON_REVISION",
            "NEON_ADDITIONAL_FEE",
            "NEON_CHAIN_ID",
            "NEON_COMPUTE_BUDGET_HEAP_FRAME",
            "NEON_POOL_COUNT",
            "NEON_HOLDER_MSG_SIZE",
            "NEON_TREASURY_POOL_COUNT",
            "NEON_TOKEN_MINT_DECIMALS",
            "NEON_EVM_ID",
        ]
        for field in expected_fields:
            assert (
                    field in response["result"]
            ), f"Field {field} is not in response: {response}"

    def test_neon_cli_version(self):
        response = self.proxy_api.send_rpc(method="neon_cli_version", params=[])
        pattern = r"Neon-cli/[vt]\d{1,2}.\d{1,2}.\d{1,2}.*"
        assert re.match(
            pattern, response["result"]
        ), f"Version format is not correct. Pattern: {pattern}; Response: {response}"
