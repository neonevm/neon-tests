import typing as tp
from dataclasses import dataclass
from dataclasses_json import CatchAll, LetterCase, dataclass_json, Undefined


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CallRequest:
    from_: tp.List[str] = None
    to: tp.List[str] = None
    gas: int = None
    gas_price: int = None
    value: int = None
    data: tp.List[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class GetLogsRequest:
    from_block: tp.Union[int, str] = None
    to_block: tp.Union[int, str] = None
    address: tp.Union[str, tp.List[str]] = None
    topics: tp.List[str] = None
    blockhash: tp.List[str] = None


# TODO: decide whether to use this class or satisfy using just a list
@dataclass
class JsonRpcRequestParams(tp.List):
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
    block_number: tp.Union[int, None]
    from_: CatchAll
    gas: int
    gas_price: int
    hash: str
    input: str
    nonce: int
    to: str
    transaction_index: tp.Union[int, None]
    value: int
    v: int
    r: str
    s: str


# commented fields aren't represented in Neon EVM
@dataclass_json(letter_case=LetterCase.CAMEL, undefined=Undefined.INCLUDE)
@dataclass(frozen=True)
class BlockResponse:
    number: tp.Union[int, None]
    hash: tp.Union[str, None]
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
    contract_address: tp.Union[str, None]
    logs: tp.List[tp.Any]
    logs_bloom: str
    # root: Any
    status: int


@dataclass
class AccountData:
    address: str
    key: str = ""
