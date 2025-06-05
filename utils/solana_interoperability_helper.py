import spl
import allure

from solana.rpc.types import TxOpts
from solana.transaction import AccountMeta, Instruction
from solders.pubkey import Pubkey
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID

from utils.consts import TRANSFER_TOKENS_ID
from utils.helpers import serialize_instruction


@allure.step("Prepare spl token and transfer instruction")
def prepare_transfer_spl_data(sol_client, from_wallet, to_wallet, amount, contract, is_set_authority=True):
    mint = SplToken.create_mint(
        conn=sol_client,
        payer=from_wallet,
        mint_authority=from_wallet.pubkey(),
        decimals=9,
        program_id=TOKEN_PROGRAM_ID,
    )
    mint.payer = from_wallet
    from_token_account = mint.create_associated_token_account(from_wallet.pubkey())
    to_token_account = mint.create_associated_token_account(to_wallet.pubkey())
    mint.mint_to(
        dest=from_token_account,
        mint_authority=from_wallet,
        amount=amount,
        opts=TxOpts(skip_confirmation=False, skip_preflight=True),
    )

    authority_pubkey: bytes = contract.functions.getSolanaPDA(bytes(TRANSFER_TOKENS_ID), b"authority").call()
    if is_set_authority:
        mint.set_authority(
            from_token_account,
            from_wallet,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            Pubkey(authority_pubkey),
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

    instruction = Instruction(
        program_id=TRANSFER_TOKENS_ID,
        accounts=[
            AccountMeta(from_token_account, is_signer=False, is_writable=True),
            AccountMeta(mint.pubkey, is_signer=False, is_writable=True),
            AccountMeta(to_token_account, is_signer=False, is_writable=True),
            AccountMeta(Pubkey(authority_pubkey), is_signer=False, is_writable=True),
            AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        data=bytes([0x0]),
    )
    return serialize_instruction(TRANSFER_TOKENS_ID, instruction), mint, [from_token_account, to_token_account]
