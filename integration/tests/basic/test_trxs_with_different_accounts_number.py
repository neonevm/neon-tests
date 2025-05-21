from web3.contract import Contract

from utils.accounts import EthAccounts
from utils.solana_client import SolanaClient
from utils.solana_data_for_neon_trx_helper import get_alt_by_neon_trx, get_sol_account_list_by_neon_trx
from utils.web3client import NeonChainWeb3Client


class TestTrxsWithDifferentAccountsCount:
    def test_trx_with_alt(
        self,
        sol_client: SolanaClient,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
        alt_contract: Contract,
    ):
        """Trigger transaction than requires more than 50 accounts"""
        sender_account = accounts[1]
        accounts_quantity = 59
        tx = web3_client.make_raw_tx(sender_account)

        instr = alt_contract.functions.fill(accounts_quantity).build_transaction(tx)
        receipt = web3_client.send_transaction(sender_account, instr)

        alt = get_alt_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
        assert alt is not None, "There are no lookup table for transaction"
        sol_accounts = get_sol_account_list_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
        assert len(sol_accounts) >= 50

        assert receipt["status"] == 1, "Transaction failed"

    def test_contract_deploy_with_alt(self, web3_client, sol_client, accounts):
        """Trigger deploy transaction than requires more than 30 accounts"""

        accounts_quantity = 50
        contract, receipt = web3_client.deploy_and_get_contract(
            "common/ALT", "0.8.10", account=accounts[0], constructor_args=[accounts_quantity]
        )

        alt = get_alt_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
        assert alt is not None, "There are no lookup table for transaction"
        sol_accounts = get_sol_account_list_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
        assert len(sol_accounts) >= 50

        assert receipt["status"] == 1, "Transaction failed"

    def test_failed_trx_with_alt(self, web3_client, sol_client, accounts, alt_contract):
        """Trigger transaction than requires more than 50 accounts and fails"""
        sender_account = accounts[1]
        accounts_quantity = 59
        tx = web3_client.make_raw_tx(from_=sender_account, gas=10000000)

        instr = alt_contract.functions.fillAndRevert(accounts_quantity).build_transaction(tx)
        receipt = web3_client.send_transaction(sender_account, instr)

        alt = get_alt_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
        assert alt is not None, "There are no lookup table for transaction"
        sol_accounts = get_sol_account_list_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
        assert len(sol_accounts) >= 50

        assert receipt["status"] == 0, "Transaction should be failed"

    def test_trx_with_big_account_count_without_alt(self, web3_client, sol_client, accounts, alt_contract):
        """Trigger transaction than requires more than 30 accounts but alt was not created"""
        sender_account = accounts[1]
        accounts_quantity = 30
        tx = web3_client.make_raw_tx(from_=sender_account)

        instr = alt_contract.functions.fill(accounts_quantity).build_transaction(tx)
        receipt = web3_client.send_transaction(sender_account, instr)

        alt = get_alt_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
        assert alt is None, "There are lookup table for transaction"
        sol_accounts = get_sol_account_list_by_neon_trx(web3_client, sol_client, receipt["transactionHash"].hex())
        assert len(sol_accounts) >= 30

        assert receipt["status"] == 1, "Transaction failed"
