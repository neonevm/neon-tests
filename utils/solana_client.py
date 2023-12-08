import json
import time
import typing as tp

import solana.rpc.api
import spl.token.client
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Commitment, Finalized
from solana.rpc.types import TxOpts
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature
from solana.system_program import TransferParams, transfer
from solana.transaction import Transaction
from solders.rpc.errors import InternalErrorMessage
from solders.rpc.responses import RequestAirdropResp
from spl.token.instructions import get_associated_token_address, create_associated_token_account, mint_to, MintToParams
from spl.token.client import Token as SplToken

from utils.consts import LAMPORT_PER_SOL, wSOL
from utils.helpers import wait_condition
from spl.token.constants import TOKEN_PROGRAM_ID

from utils.transfers_inter_networks import wSOL_tx, token_from_solana_to_neon_tx, mint_tx


class SolanaClient(solana.rpc.api.Client):
    def __init__(self, endpoint, account_seed_version="\3"):
        super().__init__(endpoint=endpoint, timeout=60)
        self.account_seed_version = (
            bytes(account_seed_version, encoding="utf-8").decode("unicode-escape").encode("utf-8")
        )

    def request_airdrop(
        self,
        pubkey: PublicKey,
        lamports: int,
        commitment: tp.Optional[Commitment] = None,
    ) -> RequestAirdropResp:
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
            transfer(TransferParams(from_pubkey=from_.public_key, to_pubkey=to, lamports=amount_lamports))
        )
        balance_before = self.get_balance(to).value
        self.send_transaction(tx, from_)
        for _ in range(20):
            if int(self.get_balance(to).value) > int(balance_before):
                break
            time.sleep(6)
        else:
            raise AssertionError(f"Balance not changed in account {to}")

    def ether2balance(self, address: tp.Union[str, bytes], chain_id: int, evm_loader_id: str) -> PublicKey:
        # get public key associated with chain_id for an address
        address_bytes = bytes.fromhex(address[2:])
        chain_id_bytes = chain_id.to_bytes(32, "big")
        return PublicKey.find_program_address(
            [self.account_seed_version, address_bytes, chain_id_bytes], PublicKey(evm_loader_id)
        )[0]

    @staticmethod
    def ether2bytes(ether: tp.Union[str, bytes]):
        if isinstance(ether, str):
            if ether.startswith("0x"):
                return bytes.fromhex(ether[2:])
            return bytes.fromhex(ether)
        return ether

    def ether2program(self, ether: tp.Union[str, bytes], evm_loader_id: str) -> tp.Tuple[str, int]:
        items = PublicKey.find_program_address(
            [self.account_seed_version, self.ether2bytes(ether)], PublicKey(evm_loader_id)
        )
        return str(items[0]), items[1]

    def get_erc_auth_address(self, neon_account_address: str, token_address: str, evm_loader_id: str):
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

    def send_tx_and_check_status_ok(self, tx, *signers):
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        sig = self.send_transaction(tx, *signers, opts=opts).value
        sig_status = json.loads((self.confirm_transaction(sig)).to_json())
        assert sig_status["result"]["value"][0]["status"] == {"Ok": None}, f"error:{sig_status}"

    def create_ata(self, solana_account, neon_mint):
        trx = Transaction()
        trx.add(create_associated_token_account(solana_account.public_key, solana_account.public_key, neon_mint))
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.send_transaction(trx, solana_account, opts=opts)

    def deposit_wrapped_sol_from_solana_to_neon(
        self, solana_account, neon_account, chain_id, evm_loader_id, full_amount=None
    ):
        if not full_amount:
            full_amount = int(0.1 * LAMPORT_PER_SOL)
        mint_pubkey = wSOL["address_spl"]
        ata_address = get_associated_token_address(solana_account.public_key, mint_pubkey)

        self.create_ata(solana_account, mint_pubkey)

        # wrap SOL
        wSOL_account = self.get_account_info(ata_address).value
        wrap_sol_tx = wSOL_tx(wSOL_account, wSOL, full_amount, solana_account.public_key, ata_address)
        self.send_tx_and_check_status_ok(wrap_sol_tx, solana_account)

        tx = token_from_solana_to_neon_tx(
            self, solana_account, wSOL["address_spl"], neon_account, full_amount, evm_loader_id, chain_id
        )

        self.send_tx_and_check_status_ok(tx, solana_account)

    def deposit_neon_like_tokens_from_solana_to_neon(
        self,
        neon_mint,
        solana_account,
        neon_account,
        chain_id,
        operator_keypair,
        evm_loader_keypair,
        evm_loader_id,
        amount,
    ):
        spl_neon_token = SplToken(self, neon_mint, TOKEN_PROGRAM_ID, payer=operator_keypair)
        associated_token_address = spl_neon_token.create_associated_token_account(solana_account.public_key)

        tx = mint_tx(
            amount=amount,
            dest=associated_token_address,
            neon_mint=neon_mint,
            mint_authority=evm_loader_keypair.public_key,
        )
        tx.fee_payer = operator_keypair.public_key

        self.send_tx_and_check_status_ok(tx, operator_keypair, evm_loader_keypair)

        tx = token_from_solana_to_neon_tx(
            self,
            solana_account,
            neon_mint,
            neon_account,
            amount,
            evm_loader_id,
            chain_id,
        )
        self.send_tx_and_check_status_ok(tx, solana_account)

    def wait_transaction(self, tx):
        try:
            wait_condition(
                lambda: self.get_transaction(Signature.from_string(tx), max_supported_transaction_version=0)
                != GetTransactionResp(None)
            )
        except TimeoutError:
            return None
        return self.get_transaction(Signature.from_string(tx), max_supported_transaction_version=0)
