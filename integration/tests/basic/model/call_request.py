from dataclasses import dataclass
from typing import List


@dataclass
class CallRequest:
    from1: List[str] = None
    to: List[str] = None
    gas: int = None
    gasPrice: int = None
    value: int = None
    data: List[str] = None
