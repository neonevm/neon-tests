import time
import typing as tp

import solana.rpc.api
import spl.token.client
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Commitment, Finalized
from solana.rpc.types import TxOpts
from solana.system_program import TransferParams, transfer
from solana.transaction import Transaction
from solders.rpc.errors import InternalErrorMessage
from solders.rpc.responses import RequestAirdropResp

from utils.helpers import wait_condition
from spl.token.constants import TOKEN_PROGRAM_ID


class SolanaClient(solana.rpc.api.Client):
    def __init__(self, endpoint, account_seed_version="\3"):
        super().__init__(endpoint=endpoint, timeout=60)
        self.account_seed_version = (
            bytes(account_seed_version, encoding="utf-8")
            .decode("unicode-escape")
            .encode("utf-8")
        )

    def request_airdrop(
        self,
        pubkey: PublicKey,
        lamports: int,
        commitment: tp.Optional[Commitment] = None,
    ) -> RequestAirdropResp:
        airdrop_resp = None
        for _ in range(5):
            airdrop_resp = super().request_airdrop(
                pubkey, lamports, commitment=Finalized
            )
            if isinstance(airdrop_resp, InternalErrorMessage):
                time.sleep(10)
                print(f"Get error from solana airdrop: {airdrop_resp}")
            else:
                break
        else:
            raise AssertionError(f"Can't get airdrop from solana: {airdrop_resp}")
        wait_condition(
            lambda: self.get_balance(pubkey).value >= lamports, timeout_sec=30
        )
        return airdrop_resp

    def send_sol(self, from_: Keypair, to: PublicKey, amount_lamports: int):
        tx = Transaction().add(
            transfer(
                TransferParams(
                    from_pubkey=from_.public_key, to_pubkey=to, lamports=amount_lamports
                )
            )
        )
        balance_before = self.get_balance(to).value
        self.send_transaction(tx, from_)
        for _ in range(20):
            if int(self.get_balance(to).value) > int(balance_before):
                break
            time.sleep(6)
        else:
            raise AssertionError(f"Balance not changed in account {to}")

    def get_neon_account_address(
        self, neon_account_address: str, evm_loader_id: str
    ) -> PublicKey:
        neon_account_addressbytes = bytes.fromhex(neon_account_address[2:])
        return PublicKey.find_program_address(
            [self.account_seed_version, neon_account_addressbytes],
            PublicKey(evm_loader_id),
        )[0]

    def get_erc_auth_address(
        self, neon_account_address: str, token_address: str, evm_loader_id: str
    ):
        neon_account_addressbytes = bytes(12) + bytes.fromhex(neon_account_address[2:])
        if token_address.startswith("0x"):
            token_address = token_address[2:]
        neon_contract_addressbytes = bytes.fromhex(token_address)
        return PublicKey.find_program_address(
            [
                self.account_seed_version,
                b"AUTH",
                neon_contract_addressbytes,
                neon_account_addressbytes,
            ],
            PublicKey(evm_loader_id),
        )[0]

    def create_spl(self, owner: Keypair, decimals: int = 9):
        token_mint = spl.token.client.Token.create_mint(
            conn=self,
            payer=owner,
            mint_authority=owner.public_key,
            decimals=decimals,
            program_id=TOKEN_PROGRAM_ID,
        )
        assoc_addr = token_mint.create_associated_token_account(owner.public_key)
        token_mint.mint_to(
            dest=assoc_addr,
            mint_authority=owner,
            amount=1000000000000000,
            opts=TxOpts(skip_confirmation=False),
        )

        return token_mint, assoc_addr
