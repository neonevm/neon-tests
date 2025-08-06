from utils.neon_layouts.layouts import CONTRACT_ACCOUNT_LAYOUT
from utils.neon_layouts.typed_neon_account import TypedNeonAccount


class ContractAccount(TypedNeonAccount):
    layout = CONTRACT_ACCOUNT_LAYOUT

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
    def generation(self) -> int:
        return self._parsed.generation

    @property
    def revision(self) -> int:
        return self._parsed.revision
