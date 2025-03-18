from eth_utils import abi
from eth_utils import to_hex
import eth_abi


class Error32602:
    CODE = -32602
    BAD_FROM_ADDRESS = "bad from-address"
    WRONG_TRANSACTION_FORMAT = "wrong transaction format"
    INVALID_PARAMETERS = "Invalid params"
    INVALID_FILTER = INVALID_PARAMETERS
    INVALID_NONCE = INVALID_PARAMETERS
    INVALID_DATA = INVALID_PARAMETERS
    INVALID_SENDER = INVALID_PARAMETERS
    INVALID_ADDRESS = INVALID_PARAMETERS
    INVALID_BLOCKHASH = INVALID_SENDER
    INVALID_TRANSACTIONID = INVALID_PARAMETERS
    INVALID_CALL = INVALID_PARAMETERS


class Error32000:
    CODE = -32000
    UNKNOWN_TRANSACTION_HASH = "unknown transaction hash"
    WRONG_CHAIN_ID = "wrong chain id"


class Error32603:
    CODE = -32603
    INTERNAL_ERROR = "Internal error"


class Error3:
    CODE = 3
    EXECUTION_REVERTED = "execution reverted"


class ContractError:
    """
    A helper class for contract errors.

    Instances of this class are created with an error signature
    (e.g. "InsufficientBalance(uint256,uint256)") and an optional list
    of parameter types (e.g. ["uint256", "uint256"]). The instance computes
    its error selector and provides methods to:
      - Validate a given revert hex string by checking if it starts with the selector.
      - Decode the revert data into its parameters.
    """

    def __init__(self, signature: str, arg_types=None):
        """
        Initialize the ContractError instance.

        :param signature: The error signature string. Example: "InsufficientBalance(uint256,uint256)"
        :param arg_types: A list of ABI types for the error parameters. Example: ["uint256", "uint256"]
                          If omitted, decoding is not available.
        """
        self.signature = signature
        self.arg_types = arg_types
        self.selector = abi.function_signature_to_4byte_selector(self.signature)[:4]

    def matches(self, error_hex_to_match: str) -> bool:
        """
        Check if the provided revert hex string matches this error's selector.

        :param error_hex_to_match: The revert error hex string (with or without "0x" prefix)
        :return: True if the error hex string starts with this error's selector, else False.
        """
        # Remove "0x" prefix if present
        if error_hex_to_match.startswith("0x"):
            error_hex_to_match = error_hex_to_match[2:]
        error_bytes = bytes.fromhex(error_hex_to_match)
        return error_bytes[:4] == self.selector

    def decode_args(self, error_hex: str):
        """
        Decode the error parameters from a revert hex string.

        :param error_hex: The revert error hex string.
        :return: A tuple of decoded parameters.
        :raises ValueError: If no arg_types were provided or if the error hex does not match.
        """
        if self.arg_types is None:
            raise ValueError("Argument types were not provided; decoding is unavailable.")
        # Remove "0x" prefix if present.
        if error_hex.startswith("0x"):
            error_hex = error_hex[2:]
        error_bytes = bytes.fromhex(error_hex)
        if not error_bytes.startswith(self.selector):
            raise ValueError("The provided error hex does not match this error signature.")
        # Remove the selector (first 4 bytes) to get the ABI encoded parameters.
        params_bytes = error_bytes[len(self.selector) :]
        return eth_abi.decode(self.arg_types, params_bytes)

    def __str__(self):
        return f"ContractError(signature={self.signature}, selector={to_hex(self.selector)})"


# if __name__ == '__main__':
#     error_hex = ('0xe450d38c000000000000000000000000ff'
#                   '9edaaeff4c07f6cc141ae693b3b4929ff5a5e'
#                   '40000000000000000000000000000000000000'
#                   '0000000000000000000000000000000000000000'
#                   '0000000000000000000000000000000000000000000000003e8')
#
#     error_expected = ContractError(
#         signature='ERC20InsufficientBalance(address, uint256, uint256)',
#         arg_types=['address', 'uint256', 'uint256']
#     )
#     assert error_expected.matches(error_hex)
#
#     print(error_expected.signature)
#
#     address, required, amount = error_expected.decode_args(error_hex)
#     print(f"{address=} {amount=} {required=}")


# if __name__ == '__main__':
#
#     error_code = ('0xe450d38c000000000000000000000000ff'
#                   '9edaaeff4c07f6cc141ae693b3b4929ff5a5e'
#                   '40000000000000000000000000000000000000'
#                   '0000000000000000000000000000000000000000'
#                   '0000000000000000000000000000000000000000000000003e8')
#
#
#     error_bytes = bytes.fromhex(error_code[2:])
#     error_signature = error_bytes[:4]
#     param_bytes = error_bytes[4:]
#
#     data = abi.function_signature_to_4byte_selector("")
#     print(data == error_signature)
#     address, required, amount = eth_abi.decode(["address", "uint256", "uint256"], param_bytes)
#     print(f'{address=}, {required=}, {amount=}')
#     error_sign = abi._abi_to_signature()
#     print(error_sign)
