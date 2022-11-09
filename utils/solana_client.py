import time
import solana.rpc.api
from solana.publickey import PublicKey
from solana.rpc.commitment import Finalized, Commitment
from solders.rpc.errors import InternalErrorMessage
import typing as tp

from solders.rpc.responses import RequestAirdropResp

from utils.helpers import wait_condition


class SolanaClient(solana.rpc.api.Client):
    def __init__(self, endpoint):
        super().__init__(endpoint=endpoint)

    def request_airdrop(self, pubkey: PublicKey, lamports: int,
                        commitment: tp.Optional[Commitment] = None) -> RequestAirdropResp:
        airdrop_resp = None
        for _ in range(5):
            airdrop_resp = super().request_airdrop(pubkey, lamports, commitment=Finalized)
            if isinstance(airdrop_resp, InternalErrorMessage):
                time.sleep(5)
                print(f"Get error from solana airdrop: {airdrop_resp}")
            else:
                break
        else:
            raise AssertionError(f"Can't get airdrop from solana: {airdrop_resp}")
        wait_condition(lambda: self.get_balance(pubkey).value >= lamports)
        return airdrop_resp
