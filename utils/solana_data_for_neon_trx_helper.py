import logging

import allure
from eth_account.signers.local import LocalAccount
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from solders.signature import Signature
from web3.types import TxParams

from utils.consts import AccountType
from utils.evm_loader import EvmLoader
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


@allure.step("Get accounts for container by emulation")
def get_accounts_for_container_by_emulation(
    web3_client: Web3Client,
    evm_loader: EvmLoader,
    instruction_tx: TxParams,
    sender: LocalAccount,
    container_address: Pubkey,
):
    signed_tx = web3_client.eth.account.sign_transaction(instruction_tx, sender.key)
    result = web3_client.get_neon_emulate(str(signed_tx.raw_transaction.hex()))
    sol_accounts = [Pubkey.from_string(item["pubkey"]) for item in result["result"]["solanaAccounts"]]
    data_accounts = evm_loader.filter_neon_accounts_by_type(sol_accounts, AccountType.STORAGE)
    balance_acc = evm_loader.filter_neon_accounts_by_type(sol_accounts, AccountType.USER_BALANCE)
    contract_accounts = evm_loader.filter_neon_accounts_by_type(sol_accounts, AccountType.CONTRACT)
    all_accounts = set(data_accounts + balance_acc + contract_accounts)
    return list(all_accounts - {container_address})
