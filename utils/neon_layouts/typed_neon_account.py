from utils.neon_layouts.layouts import TYPED_NEON_ACCOUNT_LAYOUT


class TypedNeonAccount:
    layout = TYPED_NEON_ACCOUNT_LAYOUT

    def __init__(self, data: bytes):
        self._parsed = self.layout.parse(data)

    @property
    def type(self) -> int:
        return self._parsed.type
