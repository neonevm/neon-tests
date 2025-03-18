import base58
from solders.keypair import Keypair

# Script to registrate new solana account for tests on devnet
keypair = Keypair()

s = bytes(keypair)
private_key_base58 = base58.b58encode(s).decode("utf-8")
print("open key", keypair.pubkey())
print("balance_account:", private_key_base58)
