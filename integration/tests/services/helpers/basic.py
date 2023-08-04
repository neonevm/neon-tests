import asyncio
import json
from types import SimpleNamespace

from websockets.legacy.client import WebSocketClientProtocol


async def ws_receive_all_messages(ws: WebSocketClientProtocol, timeout: int = 15) -> list:
    """Receive all the messages in websocket within a set timeout"""
    messages = []
    while True:
        try:
            r = await asyncio.wait_for(ws.recv(), timeout)
            messages.append(json.loads(r, object_hook=lambda d: SimpleNamespace(**d)))
        except asyncio.TimeoutError:
            break
    return messages
