import json
import time
import typing as tp
import uuid

import allure
import requests
import pathlib


import solana.rpc.api
import spl.token.client
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Commitment, Finalized, Confirmed
from solana.rpc.types import TxOpts
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature
from solana.system_program import TransferParams, transfer, create_account, CreateAccountParams
from solana.transaction import Transaction
from solders.rpc.errors import InternalErrorMessage
from solders.rpc.responses import RequestAirdropResp
from spl.token.instructions import get_associated_token_address, create_associated_token_account

from utils.helpers import wait_condition
from spl.token.constants import TOKEN_PROGRAM_ID


class SolanaClient(solana.rpc.api.Client):
    def __init__(self, endpoint, account_seed_version="\3"):
        super().__init__(endpoint=endpoint, timeout=120)
        self.endpoint = endpoint
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
        self.send_tx_and_check_status_ok(tx, from_)


    @staticmethod
    def ether2bytes(ether: tp.Union[str, bytes]):
        if isinstance(ether, str):
            if ether.startswith("0x"):
                return bytes.fromhex(ether[2:])
            return bytes.fromhex(ether)
        return ether


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
        statuses_resp = self.confirm_transaction(sig, commitment=Confirmed)
        sig_status = json.loads(statuses_resp.to_json())
        assert sig_status["result"]["value"][0]["status"] == {"Ok": None}, f"error:{sig_status}"

    def send_tx(self, trx: Transaction, *signers: Keypair, wait_status=Confirmed):
        result = self.send_transaction(trx, *signers,
                                         opts=TxOpts(skip_confirmation=True, preflight_commitment=wait_status))
        self.confirm_transaction(result.value, commitment=Confirmed)
        return self.get_transaction(result.value, commitment=Confirmed)

    def create_associate_token_acc(self, payer, owner, token_mint):
        if not self.account_exists(get_associated_token_address(owner.public_key, token_mint)):
            trx = Transaction()
            trx.add(create_associated_token_account(payer.public_key, owner.public_key, token_mint))
            self.send_tx_and_check_status_ok(trx, payer)

    def wait_transaction(self, tx):
        try:
            wait_condition(
                lambda: self.get_transaction(Signature.from_string(tx), max_supported_transaction_version=0)
                != GetTransactionResp(None)
            )
        except TimeoutError:
            return None
        return self.get_transaction(Signature.from_string(tx), max_supported_transaction_version=0)

    def account_exists(self, account_address) -> bool:
        try:
            account_info = self.get_account_info(PublicKey(account_address))
            if account_info.value is not None:
                return True
            else:
                return False
        except Exception as e:
            print(f"An error occurred: {e}")

    def get_account_whole_info(
        self,
        pubkey: PublicKey,
    ):
        # get_account_info method returns cut data

        body = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "getAccountInfo",
            "params": [f"{pubkey}", {"encoding": "base64", "commitment": "confirmed"}],
        }
        response = requests.post(self.endpoint, json=body, headers={"Content-Type": "application/json"})
        return response.json()

    def mint_spl_to(self, mint: PublicKey, dest: Keypair, amount: int, authority: tp.Optional[Keypair] = None):
        token_account = get_associated_token_address(dest.public_key, mint)

        self.create_associate_token_acc(dest, dest, mint)

        if authority is None:
            operator_path = pathlib.Path(__file__).parent.parent / "operator-keypair.json"
            with open(operator_path, "r") as f:
                authority = Keypair.from_seed(json.load(f)[:32])

        token = spl.token.client.Token(self, mint, TOKEN_PROGRAM_ID, authority)
        token.payer = authority
        token.mint_to(token_account, authority, amount)

    def get_solana_balance(self, account):
        return self.get_balance(account, commitment=Confirmed).value

    def create_account(self, payer, size, owner, account=None, lamports=None):
        account = account or Keypair.generate()
        lamports = lamports or self.get_minimum_balance_for_rent_exemption(size).value
        trx = Transaction()
        trx.fee_payer=payer.public_key
        instr = create_account(
            CreateAccountParams(
                payer.public_key,
                account.public_key,
                lamports,
                size,
                owner))
        self.send_tx(trx.add(instr), payer, account)
        return account

    @allure.step("Get Solana transaction with wait")
    def get_transaction_with_wait(
            self,
            tx_sig: Signature,
            encoding: str = "json",
            commitment: tp.Optional[Commitment] = None,
            max_supported_transaction_version: tp.Optional[int] = None,
    ) -> GetTransactionResp:
        tx = wait_condition(
            func_cond=lambda: super(SolanaClient, self).get_transaction(
                tx_sig=tx_sig,
                encoding=encoding,
                commitment=commitment,
                max_supported_transaction_version=max_supported_transaction_version,
            ),
            check_success=lambda trx: trx.value is not None
        )
        return tx
