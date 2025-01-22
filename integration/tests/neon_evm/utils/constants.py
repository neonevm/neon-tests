import os
from solders.pubkey import Pubkey


TREASURY_POOL_SEED = os.environ.get("NEON_TREASURY_POOL_SEED", "treasury_pool")
TREASURY_POOL_COUNT = os.environ.get("NEON_TREASURY_POOL_COUNT", 128)
ACCOUNT_SEED_VERSION = b"\3"


TAG_EMPTY = 0
TAG_FINALIZED_STATE = 32
TAG_ACTIVE_STATE = 25
TAG_HOLDER = 52
