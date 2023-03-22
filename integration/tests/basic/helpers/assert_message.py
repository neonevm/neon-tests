from enum import Enum


class ErrorMessage(Enum):
    NEGATIVE_VALUE = "Resulting wei value must be between 1 and "
    INSUFFICIENT_FUNDS = "insufficient funds for transfer"
    GAS_OVERFLOW = "gas uint64 overflow"
    GAS_LIMIT_REACHED = "gas limit reached"
    INVALID_FIELDS_GAS = "Transaction had invalid fields: {'gas'"
    NONCE_TOO_LOW = "nonce too low"
    EIP55_INVALID_CHECKSUM = (
        "'Address has an invalid EIP-55 checksum. After looking up the address from the original source, try again.'"
    )
    ALREADY_KNOWN = "already known"
    REPLACEMENT_UNDERPRICED = "replacement transaction underpriced"
    TOO_BIG_TRANSACTION = "transaction size is too big"
    TRANSACTION_UNDERPRICED = "transaction underpriced: have {} want"

    INVALID_ADDRESS = "only accepts checksum addresses"
    ZERO_ACCOUNT_ERC20 = "execution reverted: ERC20: {} the zero address"
    AMOUNT_EXCEEDS_BALANCE_ERC20 = "execution reverted: ERC20: {} amount exceeds balance"
    INSUFFICIENT_ALLOWANCE_ERC20 = "execution reverted: ERC20: insufficient allowance"
    MUST_HAVE_MINTER_ROLE_ERC20 = "execution reverted: ERC20: must have minter role to mint"

    ZERO_ACCOUNT_ERC721 = "execution reverted: ERC721: {} the zero address"
    INVALID_TOKEN_ERC721 = "ERC721: invalid token ID"
    NOT_TOKEN_OWNER_ERC721 = "execution reverted: ERC721: caller is not token owner nor approved"
    INCORRECT_OWNER_ERC721 = "execution reverted: ERC721: transfer from incorrect owner"
    APPROVAL_TO_OWNER_ERC721 = "execution reverted: ERC721: approval to current owner"
    APPROVE_CALLER_IS_NOT_OWNER_ERC721 = "ERC721: approve caller is not token owner nor approved for all"
    INVALID_RECEIVER_ERC721 = "execution reverted: ERC721: transfer to non ERC721Receiver implementer"
    APPROVE_TO_CALLER_ERC721 = "execution reverted: ERC721: approve to caller"


class AssertMessage(Enum):
    WRONG_ID = "Id of the response does not correspond to id of the request"
    WRONG_TYPE = "The response type is error response"
    DOES_NOT_START_WITH_0X = "Result does not start with 0x"
    WRONG_AMOUNT = "Wrong amount returned"
    CONTAINS_ERROR = "Contains the error data"
    DOES_NOT_CONTAIN_RESULT = "Does not contain the result data"
    DOES_NOT_CONTAIN_TOO_LOW = f"Message does not contain '{ErrorMessage.NONCE_TOO_LOW.value}'"
    CONTRACT_BALANCE_IS_WRONG = "Contract balance is wrong"
