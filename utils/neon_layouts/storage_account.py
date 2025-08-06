from utils.neon_layouts.layouts import STORAGE_CELL_LAYOUT
from utils.neon_layouts.typed_neon_account import TypedNeonAccount


class StorageAccount(TypedNeonAccount):
    layout = STORAGE_CELL_LAYOUT

    def __init__(self, data: bytes):
        super().__init__(data)

    @property
    def header_version(self) -> int:
        return self._parsed.header_version

    @property
    def revision(self) -> int:
        return self._parsed.revision
