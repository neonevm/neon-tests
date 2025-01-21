import web3
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.constants import ACCOUNT_SEED_VERSION
from utils.helpers import pubkey2neon_address


class NeonUser:
    solana_account: Keypair
    neon_address: bytes
    checksum_address: str

    def __init__(self, evm_loader: str, neon_chain_id: str):
        self.solana_account = Keypair()
        self.neon_address = pubkey2neon_address(self.solana_account.pubkey())
        self.checksum_address = web3.Web3.to_checksum_address(self.neon_address)
        self.evm_loader = evm_loader
        self.neon_chain_id = neon_chain_id

    def get_balance_account(self, chain_id: int | None = None) -> Pubkey:
        if not chain_id:
            chain_id = self.neon_chain_id
        chain_id_bytes = chain_id.to_bytes(32, "big")
        return Pubkey.find_program_address(
            [ACCOUNT_SEED_VERSION, self.neon_address, chain_id_bytes], Pubkey.from_string(self.evm_loader)
        )[0]
