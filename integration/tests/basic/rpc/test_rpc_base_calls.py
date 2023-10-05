import re
import time
import typing as tp
from enum import Enum

import allure
import pytest
import web3
from eth_utils import keccak

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.errors import Error32000, Error32602
from integration.tests.basic.helpers.rpc_checks import is_hex, assert_fields_are_hex, assert_equal_fields
from integration.tests.helpers.basic import cryptohex
from utils import helpers
from utils.helpers import gen_hash_of_block


class Tag(Enum):
    EARLIEST = "earliest"
    LATEST = "latest"
    PENDING = "pending"
    SAFE = "safe"
    FINALIZED = "finalized"


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
    _erc20_contract: tp.Optional[tp.Any] = None

    @pytest.fixture
    def erc20_contract(self) -> tp.Any:
        if not TestRpcBaseCalls._erc20_contract:
            contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
                "ERC20/ERC20.sol",
                "0.8.8",
                self.sender_account,
                contract_name="ERC20",
                constructor_args=["Test Token", "TT", 1000],
            )

            tx_receipt = self.web3_client.send_erc20(
                self.sender_account,
                self.recipient_account.address,
                amount=1,
                address=contract_deploy_tx["contractAddress"],
                abi=contract.abi,
            )
            self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
            TestRpcBaseCalls._erc20_contract = contract, contract_deploy_tx, tx_receipt
        return TestRpcBaseCalls._erc20_contract

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

    def test_eth_get_transaction_receipt_with_incorrect_hash(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt when transaction hash is not correct"""

        response = self.proxy_api.send_rpc(
            method="eth_getTransactionReceipt", params=gen_hash_of_block(31)
        )
        assert "error" in response
        assert response["error"]["message"] == "transaction-id is not hex"

    def test_eth_gas_price(self):
        """Verify implemented rpc calls work eth_gasPrice"""
        response = self.proxy_api.send_rpc("eth_gasPrice")
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid current gas price `{response['result']}` in wei"

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
        assert (
            is_hex(response["result"])
        ), f"Invalid compiled byte code in response {response['result']} at a given contract address"

    def test_eth_get_code_sender_address(self):
        """Verify implemented rpc calls work eth_getCode"""
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

    @pytest.mark.parametrize("param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, None])
    def test_eth_get_transaction_count(self, param: tp.Union[Tag, None]):
        """Verify implemented rpc calls work eth_getTransactionCount"""
        if param:
            self.send_neon(self.sender_account, self.recipient_account, 1)
            param = [self.sender_account.address, param.value]
        response = self.proxy_api.send_rpc("eth_getTransactionCount", params=param)
        if not param:
            assert "error" in response, "Error not in response"
            return
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), AssertMessage.DOES_NOT_START_WITH_0X.value

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

    @pytest.mark.parametrize("param", [32, 16, None])
    def test_eth_get_transaction_by_hash_negative(self, param: tp.Union[int, None]):
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByHash",
            params=gen_hash_of_block(param) if param else param,
        )

        if param is pow(2, 5):
            assert "error" not in response
            assert response["result"] is None, f"Invalid response: {response['result']}"
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
        assert Error32602.NOT_HEX in message, "wrong message"

    def test_eth_get_transaction_by_hash(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, amount=0.001
        )
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionByHash",
            params=receipt["transactionHash"].hex(),
        )
        assert "error" not in response
        result = response["result"]
        assert_fields_are_hex(result, [
            "blockHash",
            "blockNumber",
            "hash",
            "transactionIndex",
            "type",
            "from",
            "nonce",
            "gasPrice",
            "gas",
            "to"
        ])
        assert_equal_fields(result, receipt, [
            "blockHash",
            "blockNumber",
            "hash",
            "transactionIndex",
            "type",
            "from",
            "to"
        ], {"hash": "transactionHash"})

    def test_eth_get_transaction_receipt(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt"""
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, 10)
        transaction_hash = tx_receipt.transactionHash.hex()
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionReceipt", params=transaction_hash
        )
        assert "error" not in response
        assert "result" in response, AssertMessage.DOES_NOT_CONTAIN_RESULT
        result = response["result"]
        assert_fields_are_hex(result, [
            "transactionHash",
            "transactionIndex",
            "blockNumber",
            "blockHash",
            "cumulativeGasUsed",
            "gasUsed",
            "logsBloom",
            "status",
        ])
        assert result["status"] == "0x1", "Transaction status must be 0x1"
        assert result["transactionHash"] == transaction_hash
        assert result["blockHash"] == tx_receipt.blockHash.hex()
        assert result["from"].upper() == tx_receipt["from"].upper()
        assert result["to"].upper() == tx_receipt["to"].upper()
        assert result["contractAddress"] is None
        assert result["logs"] == []

    def test_eth_get_transaction_receipt_when_hash_doesnt_exist(self):
        """Verify implemented rpc calls work eth_getTransactionReceipt when transaction hash doesn't exist"""
        response = self.proxy_api.send_rpc(
            method="eth_getTransactionReceipt", params=gen_hash_of_block(32)
        )
        assert response["result"] is None, "Result should be None"

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
        assert int(result, 16) != 0, "expected that result is not 0, but got 0"

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
        instruction_tx = contract.functions.setData(new_data).build_transaction(self.make_tx_object())
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

    def test_eth_get_work(self):
        """Verify implemented rpc calls work eth_getWork"""
        response = self.proxy_api.send_rpc(method="eth_getWork")
        assert "error" not in response
        assert (
                len(response["result"]) >= 3
        ), f"Invalid response result: {response['result']}"

    def test_eth_hash_rate(self):
        """Verify implemented rpc calls work eth_hashrate"""
        response = self.proxy_api.send_rpc(method="eth_hashrate")
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response: {response['result']}"

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
    def test_eth_get_block_by_number_via_tags(self, quantity_tag: Tag, full_trx: bool):
        """Verify implemented rpc calls work eth_getBlockByNumber"""
        self.send_neon(self.sender_account, self.recipient_account, 10)
        params = [quantity_tag.value, full_trx]
        response = self.proxy_api.send_rpc(method="eth_getBlockByNumber", params=params)
        rpc_checks.assert_block_fields(
            response, full_trx, None, quantity_tag == Tag.PENDING
        )

    def test_get_evm_params(self):
        response = self.proxy_api.send_rpc(method="neon_getEvmParams", params=[])

        expected_fields = [
            "NEON_GAS_LIMIT_MULTIPLIER_NO_CHAINID",
            "NEON_POOL_SEED",
            "NEON_COMPUTE_BUDGET_UNITS",
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


@allure.feature("JSON-RPC validation")
@allure.story("Verify eth_estimateGas RPC call")
class TestRpcCallsMoreComplex(BaseMixin):
    account: "eth_account.signers.local.LocalAccount" = None

    @pytest.fixture(params=[(850000, 15000), (8500000, 150000), (8500000, 150000)])
    def constructor_args(self, request: tp.Any) -> tp.List[int]:
        return request.param

    @pytest.fixture(params=["BigGasFactory1", "BigGasFactory2"])
    def deploy_big_gas_requirements_contract(
            self, request: tp.Any, constructor_args: tp.List[int]
    ) -> "web3._utils.datatypes.Contract":
        """Deploy contracts"""
        self.account = self.sender_account
        #  contract
        contract_interface = helpers.get_contract_interface(
            contract="issues/Ndev49", version="0.8.10", contract_name=request.param
        )
        counter = self.web3_client.eth.contract(
            abi=contract_interface["abi"], bytecode=contract_interface["bin"]
        )
        # Build transaction
        transaction = counter.constructor(*constructor_args).build_transaction(
            {
                "chainId": self.web3_client._chain_id,
                "gas": 0,
                "gasPrice": hex(self.web3_client.gas_price()),
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.account.address
                ),
                "value": "0x0",
            }
        )
        del transaction["to"]
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=transaction)
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result, `{response['result']}`"
        transaction["gas"] = int(response["result"], 16)
        # Deploy contract
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.account.key
        )
        tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        contract_deploy_tx = self.web3_client.eth.wait_for_transaction_receipt(tx)
        return self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

    def test_eth_estimate_gas_with_big_int(
            self, deploy_big_gas_requirements_contract: tp.Any
    ) -> None:
        """Check eth_estimateGas request on contracts with big int"""
        big_gas_contract = deploy_big_gas_requirements_contract
        trx_big_gas = (
            big_gas_contract.functions.checkBigGasRequirements().build_transaction(
                {
                    "chainId": self.web3_client._chain_id,
                    "from": self.account.address,
                    "nonce": self.web3_client.eth.get_transaction_count(
                        self.account.address
                    ),
                    "gas": "0x0",
                    "gasPrice": hex(self.web3_client.gas_price()),
                    "value": "0x0",
                }
            )
        )
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=trx_big_gas)
        assert "error" not in response
        estimated_gas = int(response["result"], 16)
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result, `{response['result']}`"
        trx_big_gas["gas"] = estimated_gas
        signed_trx_big_gas = self.web3_client.eth.account.sign_transaction(
            trx_big_gas, self.account.key
        )
        raw_trx_big_gas = self.web3_client.eth.send_raw_transaction(
            signed_trx_big_gas.rawTransaction
        )
        deploy_trx_big_gas = self.web3_client.eth.wait_for_transaction_receipt(
            raw_trx_big_gas
        )
        assert deploy_trx_big_gas.get(
            "status"
        ), f"Transaction is incomplete: {deploy_trx_big_gas}"
        assert estimated_gas >= int(
            deploy_trx_big_gas["gasUsed"]
        ), "Estimated Gas < Used Gas"
