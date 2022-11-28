import time
from hashlib import sha256
from random import randrange
from typing import Union, Any

import solana.rpc.api
from eth_account.datastructures import SignedTransaction
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Finalized, Commitment, Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.rpc.errors import InternalErrorMessage
import typing as tp

from solders.rpc.responses import RequestAirdropResp, SendTransactionResp
from solders.transaction_status import TransactionConfirmationStatus

from utils.helpers import wait_condition
from utils.solana_instructions import write_holder_instruction, delete_holder_instruction, \
    create_account_with_seed_instruction, create_holder_account_instruction


class SolanaClient(solana.rpc.api.Client):

    def __init__(self, endpoint, account_seed_version="\3", evm_loader_id=None):
        super().__init__(endpoint=endpoint)
        self.account_seed_version = bytes(account_seed_version, encoding='utf-8') \
            .decode('unicode-escape').encode("utf-8")
        if evm_loader_id is not None:
            self.evm_loader = PublicKey(evm_loader_id)

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

    def wait_confirm_transaction(self, tx_sig, confirmations=0):
        timeout = 30
        elapsed_time = 0
        while elapsed_time < timeout:
            resp = self.get_signature_statuses([tx_sig])
            if resp.value[0]:
                status = resp.value[0]
                if status and (status.confirmation_status in [TransactionConfirmationStatus.Finalized,
                                                              TransactionConfirmationStatus.Confirmed]
                               and status.confirmations >= confirmations):
                    return
            sleep_time = 1
            time.sleep(sleep_time)
            elapsed_time += sleep_time
        raise RuntimeError("could not confirm transaction: ", tx_sig)

    def get_neon_account_address(self, neon_account_address: str) -> PublicKey:
        neon_account_addressbytes = bytes.fromhex(neon_account_address[2:])
        return PublicKey.find_program_address([self.account_seed_version, neon_account_addressbytes],
                                              self.evm_loader)[0]

    def create_holder(self, signer: Keypair, seed: bytes = None, size: int = None, fund: int = None, storage=None) -> \
            tuple[Union[PublicKey, Any], Union[SendTransactionResp, SendTransactionResp]]:
        if size is None:
            size = 128 * 1024
        if fund is None:
            fund = 10 ** 9
        if seed is None:
            seed = str(randrange(1000000))
        if storage is None:
            storage = PublicKey(
                sha256(bytes(signer.public_key) + bytes(seed, 'utf8') + bytes(self.evm_loader)).digest())
        trx = Transaction()
        trx.add(
            create_account_with_seed_instruction(signer.public_key, signer.public_key, seed, fund, size,
                                                 self.evm_loader),
            create_holder_account_instruction(storage, signer.public_key, self.evm_loader)
        )
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        tx_sig = self.send_transaction(trx, signer, opts=opts)
        return storage, tx_sig

    def write_transaction_to_holder_account(
            self,
            signed_tx: SignedTransaction,
            holder_account: PublicKey,
            operator: Keypair
    ):
        offset = 0
        receipts = []
        rest = signed_tx.rawTransaction
        while len(rest):
            (part, rest) = (rest[:920], rest[920:])
            trx = Transaction()
            trx.add(write_holder_instruction(operator.public_key, holder_account, signed_tx.hash, offset, part,
                                             self.evm_loader))
            receipts.append(
                self.send_transaction(
                    trx,
                    operator,
                    opts=TxOpts(skip_confirmation=True, preflight_commitment=Confirmed),
                )
            )
            offset += len(part)
        for rcpt in receipts:
            self.wait_confirm_transaction(rcpt.value)

    def delete_holder(self, del_key: PublicKey, acc: Keypair, signer: Keypair):
        trx = Transaction()
        trx.add(delete_holder_instruction(del_key, acc, signer, self.evm_loader))
        return self.send_transaction(trx, signer, opts=TxOpts(skip_preflight=False, skip_confirmation=False))
