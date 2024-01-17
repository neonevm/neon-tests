from dataclasses import dataclass
from enum import Enum


@dataclass
class AccountData:
    address: str
    key: str = ""


class Tag(Enum):
    EARLIEST = "earliest"
    LATEST = "latest"
    PENDING = "pending"
    SAFE = "safe"
    FINALIZED = "finalized"
