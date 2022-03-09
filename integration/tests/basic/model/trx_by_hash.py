from dataclasses import dataclass
from typing import Union


@dataclass
class TrxByHashResponse:
    blockHash: str
    blockNumber: Union[int, None]
    from_: str
    gas: int
    gasPrice: int
    hash: str
    input: str
    nonce: int
    to: str
    transactionIndex: Union[int, None]
    value: int
    v: int
    r: str
    s: str