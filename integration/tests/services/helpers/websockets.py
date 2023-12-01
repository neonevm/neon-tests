import asyncio
import json
from types import SimpleNamespace

from async_timeout import timeout
from websockets.legacy.client import WebSocketClientProtocol


async def ws_receive_all_messages(ws: WebSocketClientProtocol, timeout: int = 15) -> list:
    """
    Receive all the messages in websocket within a set timeout

    :param WebSocketClientProtocol ws: websocket client
    :param int timeout: in case there's no any messages on the websocket it times out after the specified seconds
    """
    messages = []
    while True:
        try:
            r = await asyncio.wait_for(ws.recv(), timeout)
            messages.append(json.loads(r, object_hook=lambda d: SimpleNamespace(**d)))
        except asyncio.TimeoutError:
            break
    return messages


async def check():
    while True:
        await asyncio.sleep(1)


async def ws_receive_messages_limit_time(ws: WebSocketClientProtocol, limit_time: int):
    """
    Receive messages in websocket for a limited time

    :param WebSocketClientProtocol ws: websocket client
    :param int limit_time: the function will be executed no more than specified time in seconds
    """
    messages = []
    try:
        async with timeout(limit_time):
            while True:
                r = await ws.recv()
                messages.append(json.loads(r, object_hook=lambda d: SimpleNamespace(**d)))
    except asyncio.exceptions.TimeoutError:
        pass

    return messages
