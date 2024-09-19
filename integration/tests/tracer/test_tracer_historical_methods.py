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


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls historical methods check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestTracerHistoricalMethods:
    _contract: tp.Optional[tp.Any] = None
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: JsonRPCSession

    def compare_values(self, value, value_to_compare):
        return math.isclose(abs(float.fromhex(value) - value_to_compare), 0.0, rel_tol=1e-9)

    def assert_invalid_params(self, response):
        assert "error" in response, "No errors in response"
        assert response["error"]["code"] == -32602, "Invalid error code"
        assert response["error"]["message"] == "Invalid params"

    # GETH: NDEV-3252
    def test_eth_call_without_params(self):
        response = self.tracer_api.send_rpc(method="eth_call", params=[None])
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_call(self, storage_object, request_type):
        sender_account = self.accounts[0]
        store_value_1 = random.randint(0, 100)
        tx_obj, request_value, _ = storage_object.call_storage(sender_account, store_value_1, request_type)

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
        tx_obj_2, request_value_2, _ = storage_object.call_storage(sender_account, store_value_2, request_type)

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
        tx_obj_3, request_value_3, _ = storage_object.call_storage(sender_account, store_value_3, request_type)
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

    # GETH: NDEV-3250
    def test_eth_call_invalid_params(self, storage_object):
        sender_account = self.accounts[0]
        store_value_1 = random.randint(0, 100)
        tx_obj, _, _ = storage_object.call_storage(sender_account, store_value_1, "blockHash")
        response = self.tracer_api.send_rpc(
            method="eth_call", req_type="blockHash", params=[tx_obj, {"blockHash": "0x0000"}]
        )
        self.assert_invalid_params(response)

    def test_eth_call_by_block_and_hash(self, storage_object):
        sender_account = self.accounts[0]
        store_value_1 = random.randint(0, 100)
        tx_obj, _, receipt = storage_object.call_storage(sender_account, store_value_1, "blockNumber")
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
    def test_eth_get_storage_at(self, storage_object, request_type):
        sender_account = self.accounts[0]
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = storage_object.call_storage(sender_account, store_value_1, request_type)

        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_getStorageAt",
                    req_type=request_type,
                    params=[storage_object.contract_address, "0x0", {request_type: request_value_1}],
                )["result"],
                0,
            )
            == store_value_1,
            timeout_sec=120,
        )

        store_value_2 = random.randint(0, 100)
        _, request_value_2, _ = storage_object.call_storage(sender_account, store_value_2, request_type)

        wait_condition(
            lambda: int(
                self.tracer_api.send_rpc(
                    method="eth_getStorageAt",
                    req_type=request_type,
                    params=[storage_object.contract_address, "0x0", {request_type: request_value_2}],
                )["result"],
                0,
            )
            == store_value_2,
            timeout_sec=120,
        )

    # GETH: NDEV-3250
    def test_eth_get_storage_at_invalid_params(self):
        response = self.tracer_api.send_rpc(
            method="eth_getTransactionCount", req_type="blockNumber", params=["0x0", {"blockNumber": "0x001"}]
        )
        self.assert_invalid_params(response)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_transaction_count(self, storage_object, request_type):
        sender_account = self.accounts[0]
        nonce = self.web3_client.eth.get_transaction_count(sender_account.address)
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = storage_object.call_storage(sender_account, store_value_1, request_type)

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
        _, receipt = storage_object.retrieve_value(sender_account)

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

    # GETH: NDEV-3250
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

    # GETH: NDEV-3250
    def test_eth_get_balance_invalid_params(self):
        sender_account = self.accounts[0]
        response = self.tracer_api.send_rpc(
            method="eth_getBalance", req_type="blockHash", params=[sender_account.address, {"blockHash": "0x0"}]
        )
        self.assert_invalid_params(response)

    # GETH: NDEV-3251, NDEV-3252
    def test_eth_get_code(self, storage_contract_with_deploy_tx):
        storage_contract_code = storage_contract_with_deploy_tx[0].functions.at(storage_contract_with_deploy_tx[1]["contractAddress"]).call().hex()
        request_type = "blockNumber"

        wait_condition(
            lambda: (
                self.tracer_api.send_rpc(
                    method="eth_getCode",
                    req_type=request_type,
                    params=[storage_contract_with_deploy_tx[0].address, 
                            {request_type: hex(storage_contract_with_deploy_tx[1]['blockNumber'] - 1)}],
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
                    params=[storage_contract_with_deploy_tx[0].address, 
                            {request_type: hex(storage_contract_with_deploy_tx[1]['blockNumber'])}],
                )
            )["result"]
            == storage_contract_code,
            timeout_sec=120,
        )

        wait_condition(
            lambda: (
                self.tracer_api.send_rpc(
                    method="eth_getCode",
                    req_type=request_type,
                    params=[storage_contract_with_deploy_tx[0].address, 
                            {request_type: hex(storage_contract_with_deploy_tx[1]['blockNumber'] + 1)}],
                )
            )["result"]
            == storage_contract_code,
            timeout_sec=120,
        )

    # GETH: NDEV-3250
    def test_eth_get_code_invalid_params(self, storage_contract_with_deploy_tx):
        response = self.tracer_api.send_rpc(
            method="eth_getCode", req_type="blockHash", 
            params=[storage_contract_with_deploy_tx[0].address, {"blockHash": "0x0002"}]
        )
        self.assert_invalid_params(response)

    def test_neon_revision(self):
        block = self.web3_client.get_block_number()
        revision = self.tracer_api.send_rpc(method="get_neon_revision", params=block)
        assert revision["result"]["neon_revision"] is not None
        assert re.match(r"^[a-fA-F\d]{40}$", revision["result"]["neon_revision"])

    @pytest.mark.parametrize("block", [-190, '{"slot": 3f08}', "oneonetwozero", ["900"]])
    def test_neon_revision_invalid_block(self, block):
        revision = self.tracer_api.send_rpc(method="get_neon_revision", params=block)
        assert "error" in revision
