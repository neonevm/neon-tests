from dataclasses import dataclass

from dataclasses_json import LetterCase, dataclass_json
from time import time
from typing import Any, List, Union


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


@dataclass
class JsonRpcRequestParams(List):
    pass


@dataclass
class JsonRpcRequest():
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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TrxByHashResponse:
    block_hash: str
    block_number: Union[int, None]
    from_: str
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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TrxReceiptResponse:
    transaction_hash: str
    transaction_index: int
    block_hash: str
    block_number: int
    from_: str
    to: str
    cumulative_gas_used: int
    gas_used: int
    contract_address: Union[str, None]
    logs: List[Any]
    logs_bloom: str
    root: Any
    status: int