import math
import random
import re
import typing as tp

import pytest
import allure

from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.apiclient import JsonRPCSession
from utils.helpers import wait_condition

# test contract code to check eth_getCode method
CONTRACT_CODE = (
    "6060604052600080fd00a165627a7a72305820e75cae05548a56ec53108e39a532f0644e4b92aa900cc9f2cf98b7ab044539380029"
)
DEPLOY_CODE = "60606040523415600e57600080fd5b603580601b6000396000f300" + CONTRACT_CODE


def store_value(sender_account, value, storage_contract, web3_client):
    nonce = web3_client.eth.get_transaction_count(sender_account.address)
    instruction_tx = storage_contract.functions.store(value).build_transaction(
        {
            "nonce": nonce,
            "gasPrice": web3_client.gas_price(),
        }
    )
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1


def retrieve_value(sender_account, storage_contract, web3_client):
    nonce = web3_client.eth.get_transaction_count(sender_account.address)
    instruction_tx = storage_contract.functions.retrieve().build_transaction(
        {
            "nonce": nonce,
            "gasPrice": web3_client.gas_price(),
        }
    )
    receipt = web3_client.send_transaction(sender_account, instruction_tx)

    assert receipt["status"] == 1
    return instruction_tx, receipt


def call_storage(sender_account, storage_contract, storage_value, request_type, web3_client):
    request_value = None
    store_value(sender_account, storage_value, storage_contract, web3_client)
    tx, receipt = retrieve_value(sender_account, storage_contract, web3_client)

    tx_obj = web3_client.make_raw_tx(
        from_=sender_account.address,
        to=storage_contract.address,
        amount=tx["value"],
        gas=hex(tx["gas"]),
        gas_price=hex(tx["gasPrice"]),
        data=tx["data"],
        estimate_gas=False,
    )
    del tx_obj["chainId"]
    del tx_obj["nonce"]

    if request_type == "blockNumber":
        request_value = hex(receipt[request_type])
    else:
        request_value = receipt[request_type].hex()
    return tx_obj, request_value, receipt


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls historical methods check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestTracerHistoricalMethods:
    _contract: tp.Optional[tp.Any] = None
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: JsonRPCSession

    @pytest.fixture
    def storage_contract(self, storage_contract, accounts, web3_client) -> tp.Any:
        sender_account = accounts[0]
        if not TestTracerHistoricalMethods._contract:
            contract = storage_contract
            TestTracerHistoricalMethods._contract = contract
        yield TestTracerHistoricalMethods._contract
        store_value(sender_account, 0, TestTracerHistoricalMethods._contract, web3_client)

    def compare_values(self, value, value_to_compare):
        return math.isclose(abs(round(int(value, 0) / 1e18, 9) - value_to_compare), 0.0, rel_tol=1e-9)

    def assert_invalid_params(self, response):
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    def test_eth_call_without_params(self):
        response = self.tracer_api.send_rpc(method="eth_call", params=[None])
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_call(self, storage_contract, request_type):
        sender_account = self.accounts[0]
        store_value_1 = random.randint(0, 100)
        tx_obj, request_value, _ = call_storage(
            sender_account, storage_contract, store_value_1, request_type, self.web3_client
        )
        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_call", req_type=request_type, params=[tx_obj, {request_type: request_value}]
                )["result"],
                0,
            )
            == store_value_1,
            timeout_sec=120,
        )

        store_value_2 = random.randint(0, 100)
        tx_obj_2, request_value_2, _ = call_storage(
            sender_account, storage_contract, store_value_2, request_type, self.web3_client
        )
        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_call", req_type=request_type, params=[tx_obj_2, {request_type: request_value_2}]
                )["result"],
                0,
            )
            == store_value_2,
            timeout_sec=120,
        )

        store_value_3 = random.randint(0, 100)
        tx_obj_3, request_value_3, _ = call_storage(self, storage_contract, store_value_3, request_type)
        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_call", req_type=request_type, params=[tx_obj_3, {request_type: request_value_3}]
                )["result"],
                0,
            )
            == store_value_3,
            timeout_sec=120,
        )

    def test_eth_call_invalid_params(self, storage_contract, web3_client):
        store_value_1 = random.randint(0, 100)
        tx_obj, _, _ = call_storage(self, storage_contract, store_value_1, "blockHash", web3_client)
        response = self.tracer_api.send_rpc(
            method="eth_call", req_type="blockHash", params=[tx_obj, {"blockHash": "0x0000"}]
        )
        self.assert_invalid_params(response)

    def test_eth_call_by_block_and_hash(self, storage_contract):
        sender_account = self.accounts[0]
        store_value_1 = random.randint(0, 100)
        tx_obj, _, receipt = call_storage(
            sender_account, storage_contract, store_value_1, "blockNumber", self.web3_client
        )
        request_value_block = hex(receipt["blockNumber"])
        request_value_hash = receipt["blockHash"].hex()

        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_call", req_type="blockNumber", params=[tx_obj, {"blockNumber": request_value_block}]
                )["result"],
                0,
            )
            == store_value_1,
            timeout_sec=120,
        )

        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_call", req_type="blockHash", params=[tx_obj, {"blockHash": request_value_hash}]
                )["result"],
                0,
            )
            == store_value_1,
            timeout_sec=120,
        )

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_storage_at(self, storage_contract, request_type):
        sender_account = self.accounts[0]
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = call_storage(
            sender_account, storage_contract, store_value_1, request_type, self.web3_client
        )

        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_getStorageAt",
                    req_type=request_type,
                    params=[storage_contract.address, "0x0", {request_type: request_value_1}],
                )["result"],
                0,
            )
            == store_value_1,
            timeout_sec=120,
        )

        store_value_2 = random.randint(0, 100)
        _, request_value_2, _ = call_storage(
            sender_account, storage_contract, store_value_2, request_type, self.web3_client
        )

        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_getStorageAt",
                    req_type=request_type,
                    params=[storage_contract.address, "0x0", {request_type: request_value_2}],
                )["result"],
                0,
            )
            == store_value_2,
            timeout_sec=120,
        )

    def test_eth_get_storage_at_invalid_params(self):
        response = self.tracer_api.send_rpc(
            method="eth_getTransactionCount", req_type="blockNumber", params=["0x0", {"blockNumber": "0x001"}]
        )
        self.assert_invalid_params(response)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_transaction_count(self, storage_contract, request_type):
        sender_account = self.accounts[0]
        nonce = self.web3_client.eth.get_transaction_count(sender_account.address)
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = call_storage(
            sender_account, storage_contract, store_value_1, request_type, self.web3_client
        )

        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_getTransactionCount",
                    req_type=request_type,
                    params=[sender_account.address, {request_type: request_value_1}],
                )["result"],
                0,
            )
            == nonce + 2,
            timeout_sec=120,
        )

        request_value_2 = None
        _, receipt = retrieve_value(sender_account, storage_contract, self.web3_client)

        if request_type == "blockNumber":
            request_value_2 = hex(receipt[request_type])
        else:
            request_value_2 = receipt[request_type].hex()

        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_getTransactionCount",
                    req_type=request_type,
                    params=[sender_account.address, {request_type: request_value_2}],
                )["result"],
                0,
            )
            == nonce + 3,
            timeout_sec=120,
        )

    def test_eth_get_transaction_count_invalid_params(self):
        response = self.tracer_api.send_rpc(
            method="eth_getTransactionCount", req_type="blockNumber", params=["0x0", {"blockNumber": "0x001"}]
        )
        self.assert_invalid_params(response)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_balance(self, request_type):
        transfer_amount = 0.1
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]

        receipt_1 = self.web3_client.send_neon(sender_account, recipient_account, transfer_amount)
        assert receipt_1["status"] == 1

        sender_balance = self.web3_client.get_balance(sender_account.address)
        recipient_balance = self.web3_client.get_balance(recipient_account.address)

        if request_type == "blockNumber":
            request_value = hex(receipt_1[request_type])
        else:
            request_value = receipt_1[request_type].hex()

        wait_condition(
            lambda: self.compare_values(
                self.tracer_api.send_rpc(
                    method="eth_getBalance",
                    req_type=request_type,
                    params=[sender_account.address, {request_type: request_value}],
                )["result"],
                sender_balance,
            ),
            timeout_sec=120,
        )

        wait_condition(
            lambda: self.compare_values(
                self.tracer_api.send_rpc(
                    method="eth_getBalance",
                    req_type=request_type,
                    params=[recipient_account.address, {request_type: request_value}],
                )["result"],
                recipient_balance,
            ),
            timeout_sec=120,
        )

        receipt_2 = self.web3_client.send_neon(sender_account, recipient_account, transfer_amount)
        assert receipt_2["status"] == 1

        sender_balance_after = self.web3_client.get_balance(sender_account.address)
        recipient_balance_after = self.web3_client.get_balance(recipient_account.address)

        if request_type == "blockNumber":
            request_value = hex(receipt_2[request_type])
        else:
            request_value = receipt_2[request_type].hex()

        wait_condition(
            lambda: self.compare_values(
                self.tracer_api.send_rpc(
                    method="eth_getBalance",
                    req_type=request_type,
                    params=[sender_account.address, {request_type: request_value}],
                )["result"],
                sender_balance_after,
            ),
            timeout_sec=120,
        )

        wait_condition(
            lambda: self.compare_values(
                self.tracer_api.send_rpc(
                    method="eth_getBalance",
                    req_type=request_type,
                    params=[recipient_account.address, {request_type: request_value}],
                )["result"],
                recipient_balance_after,
            ),
            timeout_sec=120,
        )

    def test_eth_get_balance_invalid_params(self):
        sender_account = self.accounts[0]
        response = self.tracer_api.send_rpc(
            method="eth_getBalance", req_type="blockHash", params=[sender_account.address, {"blockHash": "0x0"}]
        )
        self.assert_invalid_params(response)

    def test_eth_get_code(self):
        request_type = "blockNumber"
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        
        tx = self.web3_client.make_raw_tx(
            from_=sender_account.address,
            to=recipient_account.address,
            amount=0,
            data=bytes.fromhex(DEPLOY_CODE),
        )
        gas = self.web3_client._web3.eth.estimate_gas(tx)
        tx["gas"] = gas

        receipt = self.web3_client.send_transaction(account=sender_account, transaction=tx)
        print(receipt)
        assert receipt["status"] == 1

        wait_condition(
            lambda: (
                self.tracer_api.send_rpc(
                    method="eth_getCode",
                    req_type=request_type,
                    params=[receipt["contractAddress"], {request_type: hex(receipt[request_type] - 1)}],
                )
            )["result"]
            == "",
            timeout_sec=120,
        )

        wait_condition(
            lambda: (
                self.tracer_api.send_rpc(
                    method="eth_getCode",
                    req_type="blockHash",
                    params=[receipt["contractAddress"], {"blockHash": receipt["blockHash"].hex()}],
                )
            )["result"]
            == CONTRACT_CODE,
            timeout_sec=120,
        )

        wait_condition(
            lambda: (
                self.tracer_api.send_rpc(
                    method="eth_getCode",
                    req_type=request_type,
                    params=[receipt["contractAddress"], {request_type: hex(receipt[request_type])}],
                )
            )["result"]
            == CONTRACT_CODE,
            timeout_sec=120,
        )

    def test_eth_get_code_invalid_params(self):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(
            sender_account.address,
            amount=0,
            nonce=self.web3_client.eth.get_transaction_count(sender_account.address),
            data=bytes.fromhex(DEPLOY_CODE),
        )
        gas = self.web3_client._web3.eth.estimate_gas(tx)
        tx["gas"] = gas
        receipt = self.web3_client.send_transaction(account=sender_account, transaction=tx)
        assert receipt["status"] == 1

        response = self.tracer_api.send_rpc(
            method="eth_getCode", req_type="blockHash", params=[receipt["contractAddress"], {"blockHash": "0x0002"}]
        )

        self.assert_invalid_params(response)

    def test_neon_revision(self):
        block = self.web3_client.get_block_number()
        revision = self.tracer_api.send_rpc(method="get_neon_revision", params=block)
        assert revision["result"]["neon_revision"] is not None
        assert re.match(r"^[a-fA-F\d]{40}$", revision["result"]["neon_revision"])

    @pytest.mark.parametrize("block", [190, '{"slot": 3f08}', "oneonetwozero", ["900"]])
    def test_neon_revision_invalid_block(self, block):
        revision = self.tracer_api.send_rpc(method="get_neon_revision", params=block)
        assert "error" in revision
