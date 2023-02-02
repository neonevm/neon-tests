import time
import solana.rpc.api
from solana.publickey import PublicKey
from solana.rpc.commitment import Finalized, Commitment
from solders.rpc.errors import InternalErrorMessage
import typing as tp

from solders.rpc.responses import RequestAirdropResp

from utils.helpers import wait_condition


class SolanaClient(solana.rpc.api.Client):
    def __init__(self, endpoint, account_seed_version="\3"):
        super().__init__(endpoint=endpoint)
        self.account_seed_version = bytes(account_seed_version, encoding='utf-8') \
            .decode('unicode-escape').encode("utf-8")

    def request_airdrop(self, pubkey: PublicKey, lamports: int,
                        commitment: tp.Optional[Commitment] = None) -> RequestAirdropResp:
        airdrop_resp = None
        for _ in range(5):
            airdrop_resp = super().request_airdrop(pubkey, lamports, commitment=Finalized)
            if isinstance(airdrop_resp, InternalErrorMessage):
                time.sleep(10)
                print(f"Get error from solana airdrop: {airdrop_resp}")
            else:
                break
        else:
            raise AssertionError(f"Can't get airdrop from solana: {airdrop_resp}")
        wait_condition(lambda: self.get_balance(pubkey).value >= lamports, timeout_sec=30)
        return airdrop_resp

    def get_neon_account_address(self, neon_account_address: str, evm_loader_id: str) -> PublicKey:
        neon_account_addressbytes = bytes.fromhex(neon_account_address[2:])
        return PublicKey.find_program_address([self.account_seed_version, neon_account_addressbytes],
                                              PublicKey(evm_loader_id))[0]

    def get_erc_auth_address(self, neon_account_address: str, token_address: str, evm_loader_id: str):
        neon_account_addressbytes = bytes(12) + bytes.fromhex(neon_account_address[2:])
        if token_address.startswith("0x"):
            token_address = token_address[2:]
        neon_contract_addressbytes = bytes.fromhex(token_address)
        add = PublicKey.find_program_address(
            [self.account_seed_version, b"AUTH", neon_contract_addressbytes, neon_account_addressbytes],
            PublicKey(evm_loader_id))[0]
        return add
