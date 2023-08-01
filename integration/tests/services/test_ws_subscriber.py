import json
from types import SimpleNamespace

import allure
import pytest
import websockets

from integration.tests.basic.helpers.basic import BaseMixin

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
class TestSubscriber(BaseMixin):

    @pytest.mark.parametrize(
        "subscriber_params",
        [
            ["newHeads"],
            # ["logs"]
        ],
        ids=str
    )
    async def test_eth_subscribe(self, subscriber_params: list):
        async with websockets.connect(TEST_STAND) as ws:
            data = Subscribe(subscriber_params)
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
