from dataclasses import dataclass
from time import time
from typing import Any, List, Union


@dataclass
class BlockByHashResponse:
    number: Union[int, None]
    hash: Union[str, None]
    parenthash: str
    nonce: Union[int, None]
    sha3uncles: str
    logsbloom: Union[str, None]
    transactionsroot: Any
    stateroot: Any
    receiptsroot: Any
    miner: str
    difficulty: int
    totaldificulty: int
    extradata: Any
    size: int
    gaslimit: int
    gasused: int
    timestamp: time
    transactions: List[Any]
    uncles: List[str]
