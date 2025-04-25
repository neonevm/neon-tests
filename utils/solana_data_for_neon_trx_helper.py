import logging

import allure
from solana.rpc.commitment import Confirmed
from solders.signature import Signature

from utils.solana_client import SolanaClient
from utils.web3client import Web3Client

logger = logging.getLogger(__name__)


@allure.step("Get ALT by neon trx")
def get_alt_by_neon_trx(web3_client: Web3Client, sol_client: SolanaClient, neon_trx_hash: str):
    solana_trxs = web3_client.get_solana_trx_by_neon(neon_trx_hash)
    trx_with_alt = None
    for trx_hash in solana_trxs["result"]:
        trx = sol_client.get_transaction(
            Signature.from_string(trx_hash), max_supported_transaction_version=0, commitment=Confirmed
        )
        if trx.value.transaction.transaction.message.address_table_lookups is not None:
            trx_with_alt = trx
            break
    if trx_with_alt:
        return trx_with_alt.value.transaction.transaction.message.address_table_lookups[0].account_key
    else:
        logger.debug(f"There are no lookup table for {neon_trx_hash}")
        return None


@allure.step("Get solana account list by neon trx")
def get_sol_account_list_by_neon_trx(web3_client: Web3Client, sol_client: SolanaClient, neon_trx_hash: str):
    solana_trxs = web3_client.get_solana_trx_by_neon(neon_trx_hash)
    sol_accounts = sol_client.get_account_keys_for_transaction(solana_trxs["result"][-1])
    return sol_accounts
