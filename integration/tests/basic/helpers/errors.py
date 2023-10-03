class Error:
    code: int
    message: str

    def __init__(self, code, message):
        self.code = code
        self.message = message


MISSING_ARGUMENT = Error(-32000, "missing 1 required positional argument")
NOT_HEX = Error(-32602, "is not hex")

