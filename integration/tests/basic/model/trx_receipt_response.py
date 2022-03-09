from dataclasses import dataclass
from typing import Any, List, Union


@dataclass
class TrxReceiptResponse:
    transactionHash: str
    transactionIndex: int
    blockHash: str
    blockNumber: int
    from1: str
    to: str
    cumulativeGasUsed: int
    gasUsed: int
    contractAddress: Union[str, None]
    logs: List[Any]
    logsBloom: str
    root: Any
    status: Union[1, 0]
