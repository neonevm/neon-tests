import json
import random
import string
from types import SimpleNamespace

import allure
import pytest
import websockets
from eth_utils import keccak

from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex
from integration.tests.basic.test_rpc_calls import TestRpcCalls

TEST_STAND = "ws://159.69.194.181:8282"


class ETH:
    def __init__(self, params: list, method: str):
        self.jsonrpc = 2.0
        self.id = 1
        self.method = method
        self.params = params


class Subscribe(ETH):
    def __init__(self, params: list):
        super().__init__(params, "eth_subscribe")


class Unsubscribe(ETH):
    def __init__(self, subscription_id: str):
        super().__init__([subscription_id], "eth_unsubscribe")


@allure.feature("Websocket Subscriber")
@allure.story("Subscribe to events")
class TestSubscriber(TestRpcCalls):

    async def test_eth_subscribe(self):
        async with websockets.connect(TEST_STAND) as ws:
            data = Subscribe(["newHeads"])
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            subscription = response.result
            assert len(subscription) > 0

            self.send_neon(self.sender_account, self.recipient_account, 0.1)

            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            assert response.params.subscription == subscription
            assert len(vars(response.params.result).items()) > 0

            while len(ws.messages) > 0:  # clear all received messages
                ws.messages.popleft()

            data = Unsubscribe(subscription)
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            assert response.result == 'true'

    @pytest.mark.parametrize("param_fields", [("address", "topics"), ("topics",), ("address",), ()], ids=str)
    async def test_logs(self, param_fields):
        async with websockets.connect(TEST_STAND) as ws:
            event_caller, _ = self.web3_client.deploy_and_get_contract(
                "EventCaller", "0.8.12", self.sender_account
            )
            optional_fields = {}
            topic = False

            if "address" in param_fields:
                optional_fields["address"] = event_caller.address
            if "topics" in param_fields:
                topic = (
                        "0x" + keccak(text="AllTypes(address,uint256,string,bytes32,bool)").hex()
                )
                optional_fields["topics"] = [topic]

            params = ["logs"]
            if len(optional_fields) > 0:
                params.append(optional_fields)

            data = Subscribe(params)
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            subscription = response.result
            assert len(subscription) > 0

            number = random.randint(1, 100)
            text = "".join([random.choice(string.ascii_uppercase) for _ in range(5)])
            bytes_array = text.encode().ljust(32, b'\0')
            bol = True
            tx = self.make_tx_object()
            instruction_tx = event_caller.functions.allTypes(
                self.sender_account.address, number, text, bytes_array, bol
            ).build_transaction(tx)
            self.web3_client.send_transaction(self.sender_account, instruction_tx)

            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            assert response.params.subscription == subscription
            if topic:
                assert topic in response.params.result.topics
            assert_fields_are_hex(response.params.result,
                                  ["transactionHash", "blockHash",
                                   "blockNumber", "transactionIndex",
                                   "address", "logIndex", "data"])

            while len(ws.messages) > 0:  # clear all received messages
                ws.messages.popleft()

            data = Unsubscribe(subscription)
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            assert response.result == 'true'
