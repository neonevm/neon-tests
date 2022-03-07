from dataclasses import dataclass
from typing import List, Union


@dataclass
class GetLogsRequest:
    fromBlock: Union[int, str] = None
    toBlock: Union[int, str] = None
    address: List[str] = None
    topics: List[str] = None
    blockhash: List[str] = None
