import math
import random
import typing as tp

import pytest

import allure
from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import wait_condition

# test contract code to check eth_getCode method
CONTRACT_CODE = '6060604052600080fd00a165627a7a72305820e75cae05548a56ec53108e39a532f0644e4b92aa900cc9f2cf98b7ab044539380029'
DEPLOY_CODE = '60606040523415600e57600080fd5b603580601b6000396000f300' + CONTRACT_CODE


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls historical methods check")
class TestTracerHistoricalMethods(BaseMixin):
    _contract: tp.Optional[tp.Any] = None

    @pytest.fixture
    def storage_contract(self) -> tp.Any:
        if not TestTracerHistoricalMethods._contract:
            contract, _ = self.web3_client.deploy_and_get_contract(
                "StorageSoliditySource.sol",
                "0.8.8",
                self.sender_account,
                contract_name="Storage",
                constructor_args=[],
            )
            TestTracerHistoricalMethods._contract = contract
        yield TestTracerHistoricalMethods._contract
        self.store_value(0, TestTracerHistoricalMethods._contract)

    def store_value(self, value, storage_contract):
        nonce = self.web3_client.eth.get_transaction_count(
            self.sender_account.address
        )
        instruction_tx = storage_contract.functions.store(value).build_transaction(
            {
                "nonce": nonce,
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        receipt = self.web3_client.send_transaction(
            self.sender_account, instruction_tx)
        assert receipt["status"] == 1

    def retrieve_value(self, storage_contract):
        nonce = self.web3_client.eth.get_transaction_count(
            self.sender_account.address
        )
        instruction_tx = storage_contract.functions.retrieve().build_transaction(
            {
                "nonce": nonce,
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        receipt = self.web3_client.send_transaction(
            self.sender_account, instruction_tx)

        assert receipt["status"] == 1
        return instruction_tx, receipt

    def call_storage(self, storage_contract, storage_value, request_type):
        request_value = None
        self.store_value(storage_value, storage_contract)
        tx, reciept = self.retrieve_value(storage_contract)

        tx_obj = self.create_common_tx_obj(sender=self.sender_account.address,
                                           recipient=storage_contract.address,
                                           value=hex(tx["value"]),
                                           gas=hex(tx["gas"]),
                                           gas_price=hex(tx["gasPrice"]),
                                           data=tx["data"],
                                           estimate_gas=False)
        del tx_obj["chainId"]
        del tx_obj["nonce"]

        if request_type == "blockNumber":
            request_value = hex(reciept[request_type])
        else:
            request_value = reciept[request_type].hex()
        return tx_obj, request_value, reciept

    def compare_values(self, value, value_to_compare):
        return math.isclose(abs(round(int(value, 0) / 1e18, 9) - value_to_compare),
                            0.0,
                            rel_tol=1e-9)

    def test_eth_call_without_params(self):
        response = self.tracer_api.send_rpc(method="eth_call", params=[None])
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_call(self, storage_contract, request_type):
        store_value_1 = random.randint(0, 100)
        tx_obj, request_value, _ = self.call_storage(
            storage_contract, store_value_1, request_type)
        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type=request_type,
                                                            params=[tx_obj, {request_type: request_value}])["result"], 0) == store_value_1,
                       timeout_sec=120)

        store_value_2 = random.randint(0, 100)
        tx_obj_2, request_value_2, _ = self.call_storage(
            storage_contract, store_value_2, request_type)
        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type=request_type,
                                                            params=[tx_obj_2, {request_type: request_value_2}])["result"], 0) == store_value_2,
                       timeout_sec=120)

        store_value_3 = random.randint(0, 100)
        tx_obj_3, request_value_3, _ = self.call_storage(
            storage_contract, store_value_3, request_type)
        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type=request_type,
                                                            params=[tx_obj_3, {request_type: request_value_3}])["result"], 0) == store_value_3,
                       timeout_sec=120)

    def test_eth_call_by_block_and_hash(self, storage_contract):
        store_value_1 = random.randint(0, 100)
        tx_obj, _, reciept = self.call_storage(
            storage_contract, store_value_1, "blockNumber")
        request_value_block = hex(reciept["blockNumber"])
        request_value_hash = reciept["blockHash"].hex()

        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type="blockNumber",
                                                            params=[tx_obj, {"blockNumber": request_value_block}])["result"], 0) == store_value_1,
                       timeout_sec=120)

        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_call",
                                                            req_type="blockHash",
                                                            params=[tx_obj, {"blockHash": request_value_hash}])["result"], 0) == store_value_1,
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_storage_at(self, storage_contract, request_type):
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = self.call_storage(
            storage_contract, store_value_1, request_type)

        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_getStorageAt",
                                                            req_type=request_type,
                                                            params=[storage_contract.address,
                                                                    '0x0',
                                                                    {request_type: request_value_1}])["result"], 0) == store_value_1,
                       timeout_sec=120)

        store_value_2 = random.randint(0, 100)
        _, request_value_2, _ = self.call_storage(
            storage_contract, store_value_2, request_type)

        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_getStorageAt",
                                                            req_type=request_type,
                                                            params=[storage_contract.address,
                                                                    '0x0',
                                                                    {request_type: request_value_2}])["result"], 0) == store_value_2,
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_transaction_count(self, storage_contract, request_type):
        nonce = self.web3_client.eth.get_transaction_count(
            self.sender_account.address
        )
        store_value_1 = random.randint(0, 100)
        _, request_value_1, _ = self.call_storage(
            storage_contract, store_value_1, request_type)

        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_getTransactionCount",
                                                            req_type=request_type,
                                                            params=[self.sender_account.address,
                                                                    {request_type: request_value_1}])["result"], 0) == nonce + 2,
                       timeout_sec=120)

        request_value_2 = None
        _, reciept = self.retrieve_value(storage_contract)

        if request_type == "blockNumber":
            request_value_2 = hex(reciept[request_type])
        else:
            request_value_2 = reciept[request_type].hex()

        wait_condition(lambda: int(self.tracer_api.send_rpc(method="eth_getTransactionCount",
                                                            req_type=request_type,
                                                            params=[self.sender_account.address,
                                                                    {request_type: request_value_2}])["result"], 0) == nonce + 3,
                       timeout_sec=120)

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_get_balance(self, request_type):
        transfer_amount = 0.1

        reciept_1 = self.send_neon(
            self.sender_account, self.recipient_account, transfer_amount)
        assert reciept_1["status"] == 1

        sender_balance = round(self.get_balance_from_wei(
            self.sender_account.address), 9)
        recipient_balance = round(self.get_balance_from_wei(
            self.recipient_account.address), 9)

        if request_type == "blockNumber":
            request_value = hex(reciept_1[request_type])
        else:
            request_value = reciept_1[request_type].hex()

        wait_condition(lambda: self.compare_values(self.tracer_api.send_rpc(method="eth_getBalance",
                                                                            req_type=request_type,
                                                                            params=[self.sender_account.address,
                                                                                    {request_type: request_value}])["result"],
                                                   sender_balance),
                       timeout_sec=120)

        wait_condition(lambda: self.compare_values(self.tracer_api.send_rpc(method="eth_getBalance",
                                                                            req_type=request_type,
                                                                            params=[self.recipient_account.address,
                                                                                    {request_type: request_value}])["result"],
                                                   recipient_balance),
                       timeout_sec=120)

        reciept_2 = self.send_neon(
            self.sender_account, self.recipient_account, transfer_amount)
        assert reciept_2["status"] == 1

        sender_balance_after = round(self.get_balance_from_wei(
            self.sender_account.address), 9)
        recipient_balance_after = round(self.get_balance_from_wei(
            self.recipient_account.address), 9)

        if request_type == "blockNumber":
            request_value = hex(reciept_2[request_type])
        else:
            request_value = reciept_2[request_type].hex()

        wait_condition(lambda: self.compare_values(self.tracer_api.send_rpc(method="eth_getBalance",
                                                                            req_type=request_type,
                                                                            params=[self.sender_account.address,
                                                                                    {request_type: request_value}])["result"],
                                                   sender_balance_after),
                       timeout_sec=120)

        wait_condition(lambda: self.compare_values(self.tracer_api.send_rpc(method="eth_getBalance",
                                                                            req_type=request_type,
                                                                            params=[self.recipient_account.address,
                                                                                    {request_type: request_value}])["result"],
                                                   recipient_balance_after),
                       timeout_sec=120)

    def test_eth_get_code(self):
        request_type = "blockNumber"

        tx = self.create_common_tx_obj(sender=self.sender_account.address,
                                       value=0,
                                       nonce=self.web3_client.eth.get_transaction_count(
                                           self.sender_account.address),
                                       data=bytes.fromhex(DEPLOY_CODE))
        del tx["gas"]

        receipt = self.web3_client.send_transaction(
            account=self.sender_account, transaction=tx)
        assert receipt["status"] == 1

        wait_condition(lambda: (self.tracer_api.send_rpc(method="eth_getCode",
                                                         req_type=request_type,
                                                         params=[receipt["contractAddress"],
                                                                 {request_type: hex(receipt[request_type] - 1)}]))["result"] == "",
                       timeout_sec=120)

        wait_condition(lambda: (self.tracer_api.send_rpc(method="eth_getCode",
                                                         req_type="blockHash",
                                                         params=[receipt["contractAddress"],
                                                                 {"blockHash": receipt["blockHash"].hex()}]))["result"] == CONTRACT_CODE,
                       timeout_sec=120)

        wait_condition(lambda: (self.tracer_api.send_rpc(method="eth_getCode",
                                                         req_type=request_type,
                                                         params=[receipt["contractAddress"],
                                                                 {request_type: hex(receipt[request_type])}]))["result"] == CONTRACT_CODE,
                       timeout_sec=120)

        wait_condition(lambda: (self.tracer_api.send_rpc(method="eth_getCode",
                                                         req_type=request_type,
                                                         params=[receipt["contractAddress"],
                                                                 {request_type: hex(receipt[request_type] + 1)}]))["result"] == CONTRACT_CODE,
                       timeout_sec=120)

    @pytest.mark.skip("Not released yet")
    def test_check_neon_revision(self):
        revision = self.tracer_api.send_rpc(
            method="get_neon_revision", params={"slot": 1})
        assert revision["result"]["neon_revision"] is not None
