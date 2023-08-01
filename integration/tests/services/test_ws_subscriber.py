import asyncio
import json
from types import SimpleNamespace

import pytest
import websockets

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


class TestSubscriber:

    @pytest.mark.parametrize(
        "subscriber_params",
        [
            ["newHeads"],
            ["logs"]
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

            data = Unsubscribe(subscription)
            await ws.send(json.dumps(data.__dict__))
            r = await ws.recv()
            response = json.loads(r, object_hook=lambda d: SimpleNamespace(**d))
            assert response.result == 'true'
