import web3
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.constants import CHAIN_ID, ACCOUNT_SEED_VERSION, EVM_LOADER
from utils.helpers import pubkey2neon_address


class NeonUser:
    solana_account: Keypair
    neon_address: bytes
    checksum_address: str

    def __init__(self):
        self.solana_account = Keypair()
        self.neon_address = pubkey2neon_address(self.solana_account.pubkey())
        self.checksum_address = web3.Web3.to_checksum_address(self.neon_address)

    def get_balance_account(self, chain_id=CHAIN_ID):
        chain_id_bytes = chain_id.to_bytes(32, "big")
        return Pubkey.find_program_address(
            [ACCOUNT_SEED_VERSION, self.neon_address, chain_id_bytes], Pubkey.from_string(EVM_LOADER)
        )[0]

