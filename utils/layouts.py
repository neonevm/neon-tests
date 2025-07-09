from construct import Bytes, Int8ul, Struct, Int64ul, Int32ul


HOLDER_ACCOUNT_INFO_LAYOUT = Struct(
    "tag" / Int8ul,
    "header_version" / Int8ul,
    "owner" / Bytes(32),
    "hash" / Bytes(32),
    "len" / Int64ul,
    # Technicall, heap_offset is not a part of Holder's Header and is located at a fixed
    # memory location after the Header with some padding.
    # But, since heap_offset is located strictly before the Buffer, we can
    # treat at as a part of the Header.
    # "_padding" / Bytes(24),
    "heap_offset" / Int64ul,
)


FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT = Struct(
    "tag" / Int8ul,
    "header_version" / Int8ul,
    "owner" / Bytes(32),
    "hash" / Bytes(32),
)


CONTRACT_ACCOUNT_LAYOUT = Struct(
    "type" / Int8ul,
    "header_version" / Int8ul,
    "address" / Bytes(20),
    "chain_id" / Int64ul,
    "generation" / Int32ul,
    "revision" / Int32ul,
)

BALANCE_ACCOUNT_LAYOUT = Struct(
    "type" / Int8ul,
    "header_version" / Int8ul,
    "address" / Bytes(20),
    "chain_id" / Int64ul,
    "trx_count" / Int64ul,
    "balance" / Bytes(32),
    "revision" / Int32ul,
)

BALANCE_ACCOUNT_WITH_SOLANA_ADDRESS_LAYOUT = Struct(
    "type" / Int8ul,
    "header_version" / Int8ul,
    "address" / Bytes(20),
    "chain_id" / Int64ul,
    "trx_count" / Int64ul,
    "balance" / Bytes(32),
    "revision" / Int32ul,
    "solana_address" / Bytes(32),
)

OPERATOR_BALANCE_ACCOUNT_LAYOUT = Struct(
    "type" / Int8ul,
    "header_version" / Int8ul,
    "owner" / Bytes(32),
    "address" / Bytes(20),
    "chain_id" / Int64ul,
    "balance" / Bytes(32),
)

STORAGE_CELL_LAYOUT = Struct(
    "type" / Int8ul,
    "header_version" / Int8ul,
    "revision" / Int32ul,
)

COUNTER_ACCOUNT_LAYOUT = Struct(
    "count" / Int64ul,
)
