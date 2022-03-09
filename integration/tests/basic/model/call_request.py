from dataclasses import dataclass
from dataclasses_json import LetterCase, dataclass_json
from typing import List


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CallRequest:
    from_: List[str] = None
    to: List[str] = None
    gas: int = None
    gas_price: int = None
    value: int = None
    data: List[str] = None
