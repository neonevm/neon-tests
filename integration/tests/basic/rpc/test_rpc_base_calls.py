import time
import typing as tp

import allure
import pytest
import web3
from eth_utils import keccak

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import Tag
from integration.tests.basic.helpers.errors import Error32000, Error32602
from integration.tests.basic.helpers.rpc_checks import is_hex, hex_str_consists_not_only_of_zeros
from integration.tests.helpers.basic import cryptohex
from utils.helpers import gen_hash_of_block
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client

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
    "eth_hashrate",
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
@pytest.mark.usefixtures("accounts", "web3_client")
class TestRpcBaseCalls:
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    def test_eth_call_without_params(self, json_rpc_client):
        """Verify implemented rpc calls work eth_call without params"""
        response = json_rpc_client.send_rpc("eth_call")
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("tag", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST])
    def test_eth_call(self, tag, json_rpc_client):
        """Verify implemented rpc calls work eth_call"""
        recipient_account = self.accounts[0]
        params = [
            {"to": recipient_account.address, "data": hex(pow(10, 14))},
            tag.value,
        ]

        response = json_rpc_client.send_rpc("eth_call", params=params)
        assert "error" not in response
        assert response["result"] == "0x", f"Invalid response result, `{response['result']}`"

    def test_eth_gas_price(self, json_rpc_client):
        """Verify implemented rpc calls work eth_gasPrice"""
        response = json_rpc_client.send_rpc("eth_gasPrice")
        assert "error" not in response
        assert "result" in response
        result = response["result"]
        assert rpc_checks.is_hex(result), f"Invalid current gas price `{result}` in wei"
        assert int(result, 16) > 100000000, f"gas price should be greater 100000000, got {int(result, 16)}"

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    @pytest.mark.only_stands
    def test_eth_get_balance(self, param: tp.Union[Tag, None], json_rpc_client):
        """Verify implemented rpc calls work eth_getBalance"""
        sender_account = self.accounts[0]
        response = json_rpc_client.send_rpc(
            "eth_getBalance",
            params=[sender_account.address, param.value if param else param],
        )
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), AssertMessage.WRONG_AMOUNT.value

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    def test_eth_get_code(self, event_caller_contract, param: tp.Union[Tag, None], json_rpc_client):
        """Verify implemented rpc calls work eth_getCode"""
        response = json_rpc_client.send_rpc(
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

    def test_eth_get_code_sender_address(self, json_rpc_client):
        sender_account = self.accounts[0]
        response = json_rpc_client.send_rpc(
            "eth_getCode",
            params=[sender_account.address, Tag.LATEST.value],
        )
        assert "error" not in response
        assert response["result"] == "0x", f"Invalid response {response['result']} at a given contract address"

    def test_eth_get_code_wrong_address(self, json_rpc_client):
        """Verify implemented rpc calls work eth_getCode"""
        response = json_rpc_client.send_rpc(
            "eth_getCode",
            params=[cryptohex("12345"), Tag.LATEST.value],
        )
        assert "error" in response
        assert "message" in response["error"]
        assert "bad address" in response["error"]["message"]

    def test_web3_client_version(self, json_rpc_client):
        """Verify implemented rpc calls work web3_clientVersion"""
        response = json_rpc_client.send_rpc("web3_clientVersion")
        assert "error" not in response
        assert "Neon" in response["result"], "Invalid response result"

    def test_net_version(self, json_rpc_client):
        """Verify implemented rpc calls work work net_version"""
        response = json_rpc_client.send_rpc("net_version")
        assert "error" not in response
        assert int(response["result"]) == self.web3_client.eth.chain_id, f"Invalid response result {response['result']}"

    def test_eth_send_raw_transaction(self, json_rpc_client):
        """Verify implemented rpc calls work eth_sendRawTransaction"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=1, estimate_gas=True
        )

        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", params=signed_tx.rawTransaction.hex())
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result {response['result']}"

    def test_eth_sendRawTransaction_max_size(self, json_rpc_client):
        """Validate max size for transaction, 127 KB"""
        size = 127 * 1024
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=1, estimate_gas=True
        )

        transaction["data"] = gen_hash_of_block(size)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", params=signed_tx.rawTransaction.hex())
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result {response['result']}"

    def test_eth_sendRawTransaction_max_contract_size(self, json_rpc_client, new_account):
        """Validate max size for contract, 24 KB"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/BigMemoryValue", "0.8.12", contract_name="ValueOf24K", account=new_account
        )
        assert rpc_checks.is_hex(contract.address)

    def test_eth_block_number(self, json_rpc_client):
        """Verify implemented rpc calls work work eth_blockNumber"""
        response = json_rpc_client.send_rpc(method="eth_blockNumber")
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result {response['result']}"

    def test_eth_block_number_next_block_different(self, json_rpc_client):
        response = json_rpc_client.send_rpc(method="eth_blockNumber")
        time.sleep(1)
        response2 = json_rpc_client.send_rpc(method="eth_blockNumber")

        assert "error" not in response and response2
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result {response['result']}"
        assert rpc_checks.is_hex(response2["result"]), f"Invalid response result {response2['result']}"
        assert response["result"] != response2["result"]

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, Tag.SAFE, Tag.FINALIZED, None])
    def test_eth_get_storage_at(self, event_caller_contract, param: tp.Union[Tag, None], json_rpc_client):
        """Verify implemented rpc calls work eht_getStorageAt"""
        response = json_rpc_client.send_rpc(
            method="eth_getStorageAt",
            params=[event_caller_contract.address, hex(1), param.value] if param else param,
        )
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        result = response["result"]
        assert rpc_checks.is_hex(result), f"Invalid response: {result}"
        assert int(result, 16) == 52193458690378020725790142635571483517433973554952025871423338986830750023688

    def test_eth_get_storage_at_eq_val(self, json_rpc_client, new_account):
        """Verify implemented rpc calls work eht_getStorageAt and equal values"""
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/StorageSoliditySource", "0.8.12", contract_name="StorageMultipleVars", account=new_account
        )
        responses = [
            json_rpc_client.send_rpc("eth_getStorageAt", [contract.address, hex(0), Tag.LATEST.value]),
            json_rpc_client.send_rpc("eth_getStorageAt", [contract.address, hex(1), Tag.EARLIEST.value]),
            json_rpc_client.send_rpc("eth_getStorageAt", [contract.address, hex(2), Tag.LATEST.value]),
        ]

        for i in range(len(responses)):
            assert "error" not in responses[i]
            assert "result" in responses[i]

        assert "test" in web3.Web3.to_text(responses[0]["result"]), "wrong variable value"
        assert int(responses[1]["result"], 16) == 0, "wrong storage value"
        assert int(responses[2]["result"], 16) == 0, "wrong storage value"

        new_data = "new"

        transaction = self.web3_client.make_raw_tx(from_=new_account)
        instruction_tx = contract.functions.setData(new_data).build_transaction(transaction)
        self.web3_client.send_transaction(new_account, instruction_tx)

        response = json_rpc_client.send_rpc("eth_getStorageAt", [contract.address, hex(0), Tag.LATEST.value])
        assert "error" not in response
        assert "result" in response
        assert new_data in web3.Web3.to_text(response["result"]), "wrong variable value"

    def test_eth_mining(self, json_rpc_client):
        """Verify implemented rpc calls work eth_mining"""
        response = json_rpc_client.send_rpc(method="eth_mining")
        assert "error" not in response
        assert isinstance(response["result"], bool), f"Invalid response: {response['result']}"

    def test_eth_syncing(self, json_rpc_client):
        """Verify implemented rpc calls work eth_syncing"""
        response = json_rpc_client.send_rpc(method="eth_syncing")
        if hasattr(response, "result"):
            err_msg = f"Invalid response: {response.result}"
            if not isinstance(response["result"], bool):
                assert all(isinstance(block, int) for block in response["result"].values()), err_msg
            else:
                assert not response.result, err_msg

    def test_net_peer_count(self, json_rpc_client):
        """Verify implemented rpc calls work net_peerCount"""
        response = json_rpc_client.send_rpc(method="net_peerCount")
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response: {response['result']}"

    @pytest.mark.parametrize("param", ["0x6865", "param", None, True])
    def test_web3_sha3(self, param: tp.Union[str, None], json_rpc_client):
        """Verify implemented rpc calls work web3_sha3"""
        response = json_rpc_client.send_rpc(method="web3_sha3", params=param)
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
    def test_check_unsupported_methods(self, method: str, json_rpc_client):
        """Check that endpoint was not implemented"""
        response = json_rpc_client.send_rpc(method)
        assert "error" in response
        assert "message" in response["error"]
        assert response["error"]["message"] == f"the method {method} does not exist/is not available", response

    def test_get_evm_params(self, json_rpc_client):
        response = json_rpc_client.send_rpc(method="neon_getEvmParams", params=[])
        expected_fields = [
            "NEON_ACCOUNT_SEED_VERSION",
            "NEON_EVM_STEPS_LAST_ITERATION_MAX",
            "NEON_EVM_STEPS_MIN",
            "NEON_GAS_LIMIT_MULTIPLIER_NO_CHAINID",
            "NEON_HOLDER_MSG_SIZE",
            "NEON_OPERATOR_PRIORITY_SLOTS",
            "NEON_PAYMENT_TO_TREASURE",
            "NEON_STORAGE_ENTRIES_IN_CONTRACT_ACCOUNT",
            "NEON_TREASURY_POOL_COUNT",
            "NEON_TREASURY_POOL_SEED",
            "NEON_EVM_ID",
        ]
        for field in expected_fields:
            assert field in response["result"], f"Field {field} is not in response: {response}"
