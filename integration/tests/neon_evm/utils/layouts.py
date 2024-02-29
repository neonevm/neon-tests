from construct import Bytes, Int8ul, Struct, Int64ul, Int32ul


HOLDER_ACCOUNT_INFO_LAYOUT = Struct(
    "tag" / Int8ul,
    "header_version"/ Int8ul,
    "owner" / Bytes(32),
    "hash" / Bytes(32),
    "len" / Int64ul
)


FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT = Struct(
    "tag" / Int8ul,
    "header_version"/ Int8ul,
    "owner" / Bytes(32),
    "hash" / Bytes(32),
)


CONTRACT_ACCOUNT_LAYOUT = Struct(
    "type" / Int8ul,
    "header_version"/ Int8ul,
    "address" / Bytes(20),
    "chain_id" / Int64ul,
    "generation" / Int32ul,
    "revision" / Int32ul,
)

BALANCE_ACCOUNT_LAYOUT = Struct(
    "type" / Int8ul,
    "header_version"/ Int8ul,
    "address" / Bytes(20),
    "chain_id" / Int64ul,
    "trx_count" / Int64ul,
    "balance" / Bytes(32),
)

STORAGE_CELL_LAYOUT = Struct(
    "type" / Int8ul,
    "header_version"/ Int8ul,
    "revision" / Int32ul,
)
