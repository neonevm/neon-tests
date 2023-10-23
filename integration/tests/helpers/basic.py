import typing

from eth_utils import keccak


def cryptohex(text: str):
    return "0x" + keccak(text=text).hex()


def int_to_hex(number: int):
    return int(number).to_bytes(32, 'big').hex()


def hasattr_recursive(obj: typing.Any, attribute: str) -> bool:
    attr = attribute.split(".")
    temp_obj = obj
    for a in attr:
        if hasattr(temp_obj, a):
            temp_obj = getattr(temp_obj, a)
            continue
        return False

    return True
