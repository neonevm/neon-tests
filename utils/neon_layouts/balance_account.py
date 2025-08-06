from utils.neon_layouts.layouts import BALANCE_ACCOUNT_LAYOUT
from utils.neon_layouts.typed_neon_account import TypedNeonAccount


class BalanceAccount(TypedNeonAccount):
    layout = BALANCE_ACCOUNT_LAYOUT

    def __init__(self, data: bytes):
        super().__init__(data)

    @property
    def header_version(self) -> int:
        return self._parsed.header_version

    @property
    def address(self) -> bytes:
        return self._parsed.address

    @property
    def chain_id(self) -> int:
        return self._parsed.chain_id

    @property
    def trx_count(self) -> int:
        return self._parsed.trx_count

    @property
    def balance(self) -> int:
        return int.from_bytes(self._parsed.balance, byteorder="little")

    @property
    def revision(self) -> int:
        return self._parsed.revision
