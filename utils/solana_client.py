import json
import pathlib
import time
import typing as tp
import uuid

import allure
import base58
import requests
import solana.rpc.api
import spl.token.client
from solana.rpc import commitment
from solana.rpc.commitment import Commitment, Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.rpc.errors import InternalErrorMessage
from solders.rpc.responses import GetTransactionResp
from solders.rpc.responses import RequestAirdropResp
from solders.signature import Signature
from solders.system_program import TransferParams, transfer, create_account, CreateAccountParams
from solders.transaction_status import EncodedConfirmedTransactionWithStatusMeta
from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address, create_associated_token_account

from integration.tests.economy.const import TX_COST
from utils.consts import COMPUTE_BUDGET_ID, InstructionTags, LAMPORT_PER_SOL
from utils.helpers import wait_condition
from utils.logger import log_text_to_allure_and_stdout


def fund_solana_account(evm_loader, solana_account, bank_account, network):
    if network != "local" and bank_account is not None:
        evm_loader.send_sol(bank_account, solana_account.pubkey(), int(5 * LAMPORT_PER_SOL))
    else:
        evm_loader.request_airdrop(solana_account.pubkey(), 5 * LAMPORT_PER_SOL, commitment=commitment.Confirmed)


class SolanaClient(solana.rpc.api.Client):
    def __init__(self, endpoint, account_seed_version="\3"):
        super().__init__(endpoint=endpoint, timeout=120, commitment=Confirmed)
        self.endpoint = endpoint
        self.account_seed_version = (
            bytes(account_seed_version, encoding="utf-8").decode("unicode-escape").encode("utf-8")
        )

    @allure.step("Request airdrop")
    def request_airdrop(
        self,
        pubkey: Pubkey,
        lamports: int,
        commitment: tp.Optional[Commitment] = None,
    ) -> RequestAirdropResp:
        airdrop_resp = None
        balance_before = self.get_balance(pubkey, commitment=commitment).value
        for _ in range(5):
            airdrop_resp = super().request_airdrop(pubkey, lamports, commitment=commitment)
            if isinstance(airdrop_resp, InternalErrorMessage):
                time.sleep(10)
                log_text_to_allure_and_stdout("Error from solana airdrop", airdrop_resp)

            else:
                break
        else:
            raise AssertionError(f"Can't get airdrop from solana: {airdrop_resp}")
        wait_condition(
            lambda: self.get_balance(pubkey, commitment=commitment).value >= lamports + balance_before, timeout_sec=30
        )
        return airdrop_resp

    @allure.step("Send SOL")
    def send_sol(self, from_: Keypair, to: Pubkey, amount_lamports: int):
        tx = Transaction().add(
            transfer(TransferParams(from_pubkey=from_.pubkey(), to_pubkey=to, lamports=amount_lamports))
        )
        self.send_tx_and_check_status_ok(tx, from_)

    @allure.step("Get ERC auth address")
    def get_erc_auth_address(self, neon_account_address: str, token_address: str, evm_loader_id: str):
        neon_account_addressbytes = bytes(12) + bytes.fromhex(neon_account_address[2:])
        if token_address.startswith("0x"):
            token_address = token_address[2:]
        neon_contract_addressbytes = bytes.fromhex(token_address)
        return Pubkey.find_program_address(
            [
                self.account_seed_version,
                b"AUTH",
                neon_contract_addressbytes,
                neon_account_addressbytes,
            ],
            Pubkey.from_string(evm_loader_id),
        )[0]

    @allure.step("Create SPL token mint and associated token account")
    def create_spl(self, owner: Keypair, decimals: int = 9) -> tuple[Token, Pubkey]:
        token_mint = spl.token.client.Token.create_mint(
            conn=self,
            payer=owner,
            mint_authority=owner.pubkey(),
            decimals=decimals,
            program_id=TOKEN_PROGRAM_ID,
        )
        assoc_addr = token_mint.create_associated_token_account(owner.pubkey())
        token_mint.mint_to(
            dest=assoc_addr,
            mint_authority=owner,
            amount=1000000000000000,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        return token_mint, assoc_addr

    @allure.step("Send transaction and check status is Ok")
    def send_tx_and_check_status_ok(self, tx, *signers):
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        sig = self.send_transaction(tx, *signers, opts=opts).value
        statuses_resp = self.confirm_transaction(sig, commitment=Confirmed)
        sig_status = json.loads(statuses_resp.to_json())
        receipt = self.get_transaction(sig)
        log_text_to_allure_and_stdout("Solana trx receipt", str(receipt))
        assert sig_status["result"]["value"][0]["status"] == {"Ok": None}, f"error:{sig_status}, receipt: {receipt}"

    def send_tx(self, trx: Transaction, *signers: Keypair, wait_status=Confirmed) -> GetTransactionResp:
        result = self.send_transaction(
            trx, *signers, opts=TxOpts(skip_confirmation=True, preflight_commitment=wait_status)
        )
        self.confirm_transaction(result.value, commitment=Confirmed)
        return self.get_transaction(result.value, commitment=Confirmed)

    @allure.step("Create associated token account if not exists")
    def create_associate_token_acc(self, payer: Keypair, owner: Keypair, token_mint: Pubkey):
        ata: Pubkey = get_associated_token_address(owner.pubkey(), token_mint)
        if not self.account_exists(ata):
            trx = Transaction()
            trx.add(create_associated_token_account(payer.pubkey(), owner.pubkey(), token_mint))
            self.send_tx_and_check_status_ok(trx, payer)
        return ata

    @allure.step("Wait for transaction")
    def wait_transaction(self, tx):
        try:
            wait_condition(
                lambda: self.get_transaction(Signature.from_string(tx), max_supported_transaction_version=0)
                != GetTransactionResp(None)
            )
        except TimeoutError:
            return None
        return self.get_transaction(Signature.from_string(tx), max_supported_transaction_version=0)

    @allure.step("Check if account exists")
    def account_exists(self, account_address: Pubkey) -> bool:
        account_info = self.get_account_info(account_address, commitment=Confirmed)
        if account_info.value is not None:
            return True
        else:
            return False

    @allure.step("Get account info")
    def get_account_whole_info(
        self,
        pubkey: Pubkey,
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

    @allure.step("Mint SPL tokens to account")
    def mint_spl_to(self, mint: Pubkey, dest: Keypair, amount: int, authority: tp.Optional[Keypair] = None):
        token_account = get_associated_token_address(dest.pubkey(), mint)

        self.create_associate_token_acc(dest, dest, mint)

        if authority is None:
            operator_path = pathlib.Path(__file__).parent.parent / "operator-keypair.json"
            with open(operator_path, "r") as f:
                authority = Keypair.from_bytes(json.load(f))

        token = spl.token.client.Token(self, mint, TOKEN_PROGRAM_ID, authority)
        token.payer = authority
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        token.mint_to(token_account, authority, amount, opts=opts)

    @allure.step("Get solana balance")
    def get_solana_balance(self, account: Pubkey):
        balance = self.get_balance(account, commitment=Confirmed).value
        log_text_to_allure_and_stdout("Solana balance", f"Account: {account}, Balance: {balance} lamports")
        return self.get_balance(account, commitment=Confirmed).value

    @allure.step("Create solana account")
    def create_account(self, payer: Keypair, size: int, owner: Pubkey, account=None, lamports=None):
        account = account or Keypair()
        lamports = lamports or self.get_minimum_balance_for_rent_exemption(size).value
        trx = Transaction()
        trx.fee_payer = payer.pubkey()
        instr = create_account(
            CreateAccountParams(
                from_pubkey=payer.pubkey(), to_pubkey=account.pubkey(), lamports=lamports, space=size, owner=owner
            )
        )
        self.send_tx_and_check_status_ok(trx.add(instr), payer, account)
        return account

    @allure.step("Get account keys for solana transaction")
    def get_account_keys_for_transaction(self, sol_trx: str):
        resp = self.get_transaction(
            Signature.from_string(sol_trx), max_supported_transaction_version=0, commitment=Confirmed
        )
        log_text_to_allure_and_stdout("Solana trx", str(resp))
        trx_account_keys = resp.value.transaction.transaction.message.account_keys
        loaded_addresses = (
            resp.value.transaction.meta.loaded_addresses.readonly
            + resp.value.transaction.meta.loaded_addresses.writable
        )
        return trx_account_keys + loaded_addresses

    @allure.step("Drain SOL")
    def drain_sol(self, from_: Keypair, to: Pubkey):
        balance = self.get_solana_balance(from_.pubkey())
        amount_lamports = max(0, balance - TX_COST)

        if amount_lamports > 0:
            self.send_sol(
                from_=from_,
                to=to,
                amount_lamports=amount_lamports,
            )

    @allure.step("Get ComputeBudget setComputeUnitPrice from transaction")
    def get_compute_budget_set_cu_price_from_tx(
        self,
        tx: EncodedConfirmedTransactionWithStatusMeta,
    ) -> int | None:
        """
        :param tx:
        :return: setComputeUnitPrice value from ComputeBudget instruction if it exists
        """
        # get ComputeBudget key index
        compute_budget_index = -1
        for index, account_key in enumerate(tx.transaction.transaction.message.account_keys):
            if account_key == COMPUTE_BUDGET_ID:
                compute_budget_index = index
                break

        if compute_budget_index >= 0:
            # get setComputeUnitPrice value
            for instruction in tx.transaction.transaction.message.instructions:
                if instruction.program_id_index == compute_budget_index:
                    decoded_data = base58.b58decode(instruction.data)
                    instruction_code = decoded_data[:1]
                    instruction_data = int.from_bytes(decoded_data[1:], "little")
                    if instruction_code == InstructionTags.SET_COMPUTE_UNIT_PRICE:
                        set_cu_price = instruction_data
                        return set_cu_price
