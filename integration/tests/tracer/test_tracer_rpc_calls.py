import typing as tp
import allure
import pytest
from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import wait_condition


@allure.story("Tracer API RPC calls check")
class TestTracerRpcCalls(BaseMixin):
    _contract: tp.Optional[tp.Any] = None

    @pytest.fixture
    def storage_contract(self) -> tp.Any:
        if not TestTracerRpcCalls._contract:
            contract, _ = self.web3_client.deploy_and_get_contract(
                "StorageSoliditySource.sol",
                "0.8.8",
                self.sender_account,
                contract_name="Storage",
                constructor_args=[],
            )
            TestTracerRpcCalls._contract = contract
        yield TestTracerRpcCalls._contract
        self.store_value(0, TestTracerRpcCalls._contract)

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
        return instruction_tx, receipt

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
        print("receipt:", receipt)
        print("instruction_tx:", instruction_tx)
        assert receipt["status"] == 1
        return instruction_tx, receipt

    def make_tx_object(self, sender=None, receiver=None, tx=None) -> tp.Dict:
        if sender is None:
            sender = self.sender_account.address

        tx_call_obj = {
            "from": sender,
            "to": receiver,
            "value": hex(tx["value"]),
            "gas": hex(tx["gas"]),
            "gasPrice": hex(tx["gasPrice"]),
            "data": tx["data"],
        }

        return tx_call_obj

    def call_storage(self, storage_contract, storage_value, request_type):
        request_value = None
        _, _ = self.store_value(storage_value, storage_contract)
        tx, reciept = self.retrieve_value(storage_contract)
        tx_obj = self.make_tx_object(
            self.sender_account.address, storage_contract.address, tx)

        if request_type == "blockNumber":
            request_value = hex(reciept[request_type])
        else:
            request_value = reciept[request_type].hex()
        return tx_obj, request_value

    def test_eth_call_without_params(self):
        response = self.tracer_api.send_rpc(method="eth_call", params=[None])
        assert "error" in response, "Error not in response"

    @pytest.mark.parametrize("request_type", ["blockNumber", "blockHash"])
    def test_eth_call(self, storage_contract, request_type):
        tx_obj, request_value = self.call_storage(
            storage_contract, 1, request_type)
        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_call",
                                                                   req_type=request_type,
                                                                   params=[tx_obj, {request_type: request_value}])["result"], 0) == 1,
                       timeout_sec=120)

        tx_obj_2, request_value_2 = self.call_storage(
            storage_contract, 2, request_type)
        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_call",
                                                                   req_type=request_type,
                                                                   params=[tx_obj_2, {request_type: request_value_2}])["result"], 0) == 2,
                       timeout_sec=120)

        tx_obj_3, request_value_3 = self.call_storage(
            storage_contract, 3, request_type)
        wait_condition(lambda: int(self.tracer_api.tracer_send_rpc(method="eth_call",
                                                                   req_type=request_type,
                                                                   params=[tx_obj_3, {request_type: request_value_3}])["result"], 0) == 3,
                       timeout_sec=120)
