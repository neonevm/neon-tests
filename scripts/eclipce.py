import json
import time

import web3
import typing as tp

import solana.rpc.api
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.commitment import Finalized
from solana.rpc.types import TxOpts
from solana.transaction import Transaction, AccountMeta, Instruction
from solders.rpc.errors import InternalErrorMessage
from solders.rpc.responses import RequestAirdropResp
from spl.token.instructions import get_associated_token_address, create_associated_token_account, approve, ApproveParams
import solders.system_program as sp
from spl.token.constants import TOKEN_PROGRAM_ID


# Description: This script is used to deposit native tokens to the Neon EVM.
# It wraps SOL to wSOL and sends it to the Neon EVM.
# works only for neon evm 1.4.x

PROXY_URL = "http://localhost:9090/solana"
SOLANA_URL = "http://localhost:8899/"
LOADER_ID = Pubkey.from_string("6HALMT8ZvZz3p9zigdUdn7bZ4ae3nrSSNNDV8qRZm22q")
AMOUNT = 1_000_000_000
MINT_PUBKEY = Pubkey.from_string("So11111111111111111111111111111111111111112")
RECIPIENT = ""  # New account will be created if empty


web3_client = web3.Web3(web3.HTTPProvider(PROXY_URL, request_kwargs={"timeout": 30}))


def wait_condition(func_cond, timeout_sec=15, delay=0.5):
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout_sec:
            raise TimeoutError(f"The condition not reached within {timeout_sec} sec")
        try:
            if func_cond():
                break

        except Exception as e:
            print(f"Error during waiting: {e}")
        time.sleep(delay)
    return True


class SolanaClient(solana.rpc.api.Client):
    def __init__(self, endpoint, account_seed_version="\3"):
        super().__init__(endpoint=endpoint, timeout=120)
        self.endpoint = endpoint
        self.account_seed_version = (
            bytes(account_seed_version, encoding="utf-8").decode("unicode-escape").encode("utf-8")
        )

    def request_airdrop(self, pubkey: Pubkey, lamports: int) -> RequestAirdropResp:
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

    @staticmethod
    def ether2bytes(ether: tp.Union[str, bytes]):
        if isinstance(ether, str):
            if ether.startswith("0x"):
                return bytes.fromhex(ether[2:])
            return bytes.fromhex(ether)
        return ether

    def send_tx_and_check_status_ok(self, tx, *signers):
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        sig = self.send_transaction(tx, *signers, opts=opts).value
        sig_status = json.loads((self.confirm_transaction(sig)).to_json())
        assert sig_status["result"]["value"][0]["status"] == {"Ok": None}, f"error:{sig_status}"

    def create_ata(self, solana_account: Keypair, token_mint):
        trx = Transaction()
        trx.add(create_associated_token_account(solana_account.pubkey(), solana_account.pubkey(), token_mint))
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.send_transaction(trx, solana_account, opts=opts)

    def ether2program(self, ether: tp.Union[str, bytes]) -> tp.Tuple[str, int]:
        items = Pubkey.find_program_address([self.account_seed_version, self.ether2bytes(ether)], LOADER_ID)
        return str(items[0]), items[1]

    def sent_token_from_solana_to_neon(self, solana_account: Keypair, mint, neon_account, amount):
        contract_pubkey = Pubkey.from_string(self.ether2program(neon_account)[0])
        associated_token_address = get_associated_token_address(solana_account.pubkey(), mint)
        authority_pool = Pubkey.find_program_address([b"Deposit"], LOADER_ID)[0]

        pool = get_associated_token_address(authority_pool, mint)

        tx = Transaction(fee_payer=solana_account.pubkey())
        tx.add(
            approve(
                ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=associated_token_address,
                    delegate=contract_pubkey,
                    owner=solana_account.pubkey(),
                    amount=amount,
                )
            )
        )

        tx.add(
            make_deposit(
                bytes.fromhex(neon_account[2:]),
                contract_pubkey,
                associated_token_address,
                pool,
                TOKEN_PROGRAM_ID,
                solana_account.pubkey(),
                LOADER_ID,
            )
        )
        self.send_tx_and_check_status_ok(tx, solana_account)


def make_wsol(amount, solana_wallet, associated_address):
    tx = Transaction(fee_payer=solana_wallet)
    tx.add(sp.transfer(sp.TransferParams(
        from_pubkey=solana_wallet, 
        to_pubkey=associated_address, 
        lamports=amount),
    ))

    sync_native_instr = Instruction(
        accounts=[AccountMeta(pubkey=associated_address, is_signer=False, is_writable=True)],
        program_id=TOKEN_PROGRAM_ID,
        data=bytes.fromhex("11"),
    )
    tx.add(sync_native_instr)
    return tx


def make_deposit(
    ether_address: bytes,
    solana_account: Pubkey,
    source: Pubkey,
    pool: Pubkey,
    token_program: Pubkey,
    operator_pubkey: Pubkey,
    evm_loader_id: Pubkey,
) -> Instruction:
    data = bytes.fromhex("27") + ether_address

    accounts = [
        AccountMeta(pubkey=source, is_signer=False, is_writable=True),
        AccountMeta(pubkey=pool, is_signer=False, is_writable=True),
        AccountMeta(pubkey=solana_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=token_program, is_signer=False, is_writable=False),
        AccountMeta(pubkey=operator_pubkey, is_signer=True, is_writable=True),
        AccountMeta(pubkey=sp.ID, is_signer=False, is_writable=False),
    ]

    return Instruction(program_id=evm_loader_id, data=data, accounts=accounts)


solana_client = SolanaClient(endpoint=SOLANA_URL)

if not RECIPIENT:
    new_account = web3_client.eth.account.create()
    print("New account created: ", new_account.address)
    print("private key: ", new_account.key.hex())
    recipient = new_account.address
else:
    recipient = RECIPIENT


sol_account = Keypair()
solana_client.request_airdrop(sol_account.pubkey(), 10 * AMOUNT)
# with open("sol_account_with_tokens-keypair.json", "r") as key:
#     secret_key = json.load(key)[:32]
#     sol_account = Keypair.from_secret_key(secret_key)

ata_address = get_associated_token_address(sol_account.pubkey(), MINT_PUBKEY)

solana_client.create_ata(sol_account, MINT_PUBKEY)

# wrap SOL
wrap_sol_tx = make_wsol(AMOUNT, sol_account.pubkey(), ata_address)
solana_client.send_tx_and_check_status_ok(wrap_sol_tx, sol_account)

solana_client.sent_token_from_solana_to_neon(sol_account, MINT_PUBKEY, recipient, AMOUNT)

print(f"Final balance: {web3_client.eth.get_balance(recipient)}")
