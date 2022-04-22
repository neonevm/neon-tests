from dataclasses import dataclass
from typing import Any, List, Union

from dataclasses_json import CatchAll, LetterCase, dataclass_json, Undefined


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CallRequest:
    from_: List[str] = None
    to: List[str] = None
    gas: int = None
    gas_price: int = None
    value: int = None
    data: List[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class GetLogsRequest:
    from_block: Union[int, str] = None
    to_block: Union[int, str] = None
    address: Union[str, List[str]] = None
    topics: List[str] = None
    blockhash: List[str] = None


# TODO: decide whether to use this class or satisfy using just a list
@dataclass
class JsonRpcRequestParams(List):
    pass


@dataclass
class JsonRpcRequest:
    id: int
    method: str
    params: JsonRpcRequestParams
    jsonrpc: str = "2.0"


@dataclass
class JsonRpcResponse:
    id: int
    result: object
    jsonrpc: str = "2.0"


@dataclass
class JsonRpcErrorResponse:
    id: int
    error: object
    jsonrpc: str = "2.0"


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.INCLUDE)
@dataclass
class TrxResponse:
    block_hash: str
    block_number: Union[int, None]
    from_: CatchAll
    gas: int
    gas_price: int
    hash: str
    input: str
    nonce: int
    to: str
    transaction_index: Union[int, None]
    value: int
    v: int
    r: str
    s: str


# commented fields aren't represented in Neon EVM
@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.INCLUDE)
@dataclass(frozen=True)
class BlockResponse:
    number: Union[int, None]
    hash: Union[str, None]
    parent_hash: str
    # nonce: Optional[Union[int, None]]
    # sha3_uncles: Optional[str]
    # logs_bloom: Optional[Union[str, None]]
    # transactions_root: Optional[Any]
    # state_root: Optional[Any]
    # receipts_root: Optional[Any]
    # miner: Optional[str]
    # difficulty: Optional[int]
    # total_dificulty: Optional[int]
    # extra_data: Optional[Any]
    # size: Optional[int]
    gas_limit: int
    gas_used: int
    timestamp: int
    # transactions: Optional[List[TrxByResponse]]
    # uncles: Optional[List[str]]
    unknown: CatchAll


@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.INCLUDE)
@dataclass(frozen=True)
class TrxReceiptResponse:
    transaction_hash: str
    transaction_index: int
    block_hash: str
    block_number: int
    from_: CatchAll
    to: str
    cumulative_gas_used: int
    gas_used: int
    contract_address: Union[str, None]
    logs: List[Any]
    logs_bloom: str
    # root: Any
    status: int


@dataclass
class AccountData:
    address: str
    key: str = ""
