from dataclasses import dataclass
from dataclasses_json import LetterCase, dataclass_json
from typing import List, Union


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class GetLogsRequest:
    from_block: Union[int, str] = None
    to_block: Union[int, str] = None
    address: Union[str, List[str]] = None
    topics: List[str] = None
    blockhash: List[str] = None
