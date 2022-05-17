from enum import Enum
import os


class InputData(Enum):
    FAUCET_1ST_REQUEST_AMOUNT = 1_000
    FAUCET_2ND_REQUEST_AMOUNT = 3
    DEFAULT_TRANSFER_AMOUNT = 0.01
    NEGATIVE_AMOUNT = -0.1
    SAMPLE_AMOUNT = 0.02
    ROUND_DIGITS = 3

    def get_transfer_amount(self) -> int:
        return self.DEFAULT_TRANSFER_AMOUNT.value

    def get_default_initial_amount(self) -> int:
        return self.FAUCET_1ST_REQUEST_AMOUNT.value


def gen_hash_of_block(size: int) -> str:
    """Generates a block hash of the given size"""
    try:
        block_hash = hex(int.from_bytes(os.urandom(size), "big"))
        if bytes.fromhex(block_hash[2:]):
            return block_hash
    except ValueError:
        return gen_hash_of_block(size)
