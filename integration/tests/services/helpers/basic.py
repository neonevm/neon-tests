import asyncio
import json
import typing
from types import SimpleNamespace

from eth_utils import keccak
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


def cryptohex(text: str):
    return "0x" + keccak(text=text).hex()


def hasattr_recursive(obj: typing.Any, attribute: str) -> bool:
    attr = attribute.split(".")
    temp_obj = obj
    for a in attr:
        if hasattr(temp_obj, a):
            temp_obj = getattr(temp_obj, a)
            continue
        return False

    return True
