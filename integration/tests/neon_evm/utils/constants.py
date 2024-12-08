import os
from solders.pubkey import Pubkey


TREASURY_POOL_SEED = os.environ.get("NEON_TREASURY_POOL_SEED", "treasury_pool")
TREASURY_POOL_COUNT = os.environ.get("NEON_TREASURY_POOL_COUNT", 128)
ACCOUNT_SEED_VERSION = b"\3"


TAG_EMPTY = 0
TAG_FINALIZED_STATE = 32
TAG_ACTIVE_STATE = 25
TAG_HOLDER = 52


SOLANA_URL = os.environ.get("SOLANA_URL", "http://solana:8899")
NEON_CORE_API_URL = os.environ.get("NEON_CORE_API_URL", "http://neon_api:8085/api")
NEON_CORE_API_RPC_URL = os.environ.get("NEON_CORE_API_RPC_URL", "http://neon_core_rpc:3100")

EVM_LOADER = os.environ.get("EVM_LOADER", "53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io")
NEON_TOKEN_MINT_ID: Pubkey = Pubkey.from_string(
    os.environ.get("NEON_TOKEN_MINT") or "HPsV9Deocecw3GeZv1FkAPNCBRfuVyfw9MMwjwRe1xaU"
)
SOL_MINT_ID: Pubkey = Pubkey.from_string("So11111111111111111111111111111111111111112")

CHAIN_ID = int(os.environ.get("NEON_CHAIN_ID", 111))
SOL_CHAIN_ID = int(os.environ.get("SOL_CHAIN_ID", 112))
