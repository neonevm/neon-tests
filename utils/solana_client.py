import time
import typing as tp

import solana.rpc.api
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Commitment, Finalized
from solana.system_program import SYS_PROGRAM_ID, TransferParams, transfer
from solana.transaction import AccountMeta, Transaction, TransactionInstruction
from solders.rpc.errors import InternalErrorMessage
from solders.rpc.responses import RequestAirdropResp
from spl.token.instructions import (
    ApproveParams, approve, get_associated_token_address)
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from utils.helpers import wait_condition

CreateAccountV03 = 0x28  # 40


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

    def send_sol(self, from_: Keypair, to: PublicKey, amount_lamports: int):
        tx = Transaction().add(
            transfer(
                TransferParams(from_pubkey=from_.public_key, to_pubkey=to, lamports=amount_lamports)
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

    def transaction_send_neon(self, solana_account, neon_wallet, neon_mint, neon_account, amount, evm_loader_id):
        tx = Transaction(fee_payer=solana_account.public_key)
        associated_token_address = get_associated_token_address(
            solana_account.public_key, neon_mint)
        
        tx.add(self.get_account_v3_instruction(
            solana_account.public_key,
            neon_wallet,
            neon_account.address,
            evm_loader_id)
        )

        tx.add(approve(ApproveParams(
            program_id=TOKEN_PROGRAM_ID,
            source=associated_token_address,
            delegate=neon_wallet,
            owner=solana_account.public_key,
            amount=amount))
        )

        authority_pool = self.get_authority_pool_address(
            evm_loader_id)

        tx.add(self.get_deposit_instruction(
            solana_account.public_key,
            neon_wallet,
            authority_pool,
            neon_account.address,
            neon_mint,
            evm_loader_id)
        )

        return tx

    def get_account_v3_instruction(self, solana_account, neon_wallet_pda,
                                   neon_wallet, evm_loader_id) -> TransactionInstruction:
        keys = [
            AccountMeta(pubkey=solana_account,
                        is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYS_PROGRAM_ID,
                        is_signer=False, is_writable=False),
            AccountMeta(pubkey=neon_wallet_pda,
                        is_signer=False, is_writable=True),
        ]

        data = data = bytes.fromhex('28') + bytes.fromhex(neon_wallet[2:])
        return TransactionInstruction(
            program_id=PublicKey(evm_loader_id),
            keys=keys,
            data=data)

    def get_deposit_instruction(self, solana_pubkey, neon_pubkey, deposit_pubkey, neon_wallet_address, neon_mint, evm_loader_id):
        associated_token_address = get_associated_token_address(
            solana_pubkey, neon_mint)
        pool_key = get_associated_token_address(deposit_pubkey, neon_mint)
        keys = [
            AccountMeta(pubkey=associated_token_address,
                        is_signer=False, is_writable=True),
            AccountMeta(pubkey=pool_key, is_signer=False, is_writable=True),
            AccountMeta(pubkey=neon_pubkey, is_signer=False, is_writable=True),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID,
                        is_signer=False, is_writable=False),
            AccountMeta(pubkey=solana_pubkey,
                        is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYS_PROGRAM_ID,
                        is_signer=False, is_writable=False),
        ]

        data = bytes.fromhex('27') + bytes.fromhex(neon_wallet_address[2:])
        return TransactionInstruction(
            program_id=PublicKey(evm_loader_id),
            keys=keys,
            data=data)

    def get_neon_account_address(self, neon_account_address: str, evm_loader_id: str) -> PublicKey:
        neon_account_addressbytes = bytes.fromhex(neon_account_address[2:])
        return PublicKey.find_program_address([self.account_seed_version, neon_account_addressbytes],
                                              PublicKey(evm_loader_id))[0]

    def get_erc_auth_address(self, neon_account_address: str, token_address: str, evm_loader_id: str):
        neon_account_addressbytes = bytes(12) + bytes.fromhex(neon_account_address[2:])
        if token_address.startswith("0x"):
            token_address = token_address[2:]
        neon_contract_addressbytes = bytes.fromhex(token_address)
        return PublicKey.find_program_address(
            [self.account_seed_version, b"AUTH",
                neon_contract_addressbytes, neon_account_addressbytes],
            PublicKey(evm_loader_id))[0]

    def get_authority_pool_address(self, evm_loader_id: str):
        text = 'Deposit'
        return PublicKey.find_program_address([text.encode()], PublicKey(evm_loader_id))[0]
