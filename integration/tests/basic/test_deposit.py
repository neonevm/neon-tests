import pytest
import allure
import web3
from _pytest.config import Config
from solders.keypair import Keypair
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.pubkey import Pubkey
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import create_associated_token_account, get_associated_token_address
from web3 import exceptions as web3_exceptions

from utils.consts import LAMPORT_PER_SOL, wSOL, MULTITOKEN_MINTS
from utils.instructions import make_wSOL
from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.solana_client import SolanaClient


@allure.feature("Transfer NEON <-> Solana")
@allure.story("Deposit from Solana to NEON")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client", "evm_loader")
class TestDeposit:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def withdraw_neon(self, sender_account, dest_acc: Keypair, move_amount):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "precompiled/NeonToken", "0.8.10", account=sender_account
        )
        tx = self.web3_client.make_raw_tx(sender_account, amount=web3.Web3.to_wei(move_amount, "ether"))
        instruction_tx = contract.functions.withdraw(bytes(dest_acc.pubkey())).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

    @pytest.mark.mainnet
    def test_transfer_neon_from_solana_to_neon(self, solana_account: Keypair, neon_mint, evm_loader):
        """Transfer Neon from Solana -> Neon"""
        amount = 0.1
        sender_account = self.accounts[0]
        full_amount = int(amount * LAMPORT_PER_SOL)
        new_account = self.accounts.create_account()
        neon_balance_before = self.web3_client.get_balance(new_account.address)

        self.withdraw_neon(sender_account, solana_account, amount)
        evm_loader.sent_token_from_solana_to_neon(
            solana_account,
            neon_mint,
            new_account,
            full_amount,
            self.web3_client.chain_id,
        )

        neon_balance_after = self.web3_client.get_balance(new_account.address)
        assert neon_balance_after == neon_balance_before + web3.Web3.to_wei(amount, "ether")

    @pytest.mark.multipletokens
    def test_create_and_transfer_new_token_from_solana_to_neon(
        self, solana_account, pytestconfig: Config, neon_mint, web3_client_usdt, operator_keypair, evm_loader
    ):
        amount = 5000
        new_sol_account = Keypair()
        token_mint = Pubkey.from_string(MULTITOKEN_MINTS["USDT"])
        evm_loader.request_airdrop(new_sol_account.pubkey(), 1 * LAMPORT_PER_SOL)
        new_account = self.accounts.create_account()

        evm_loader.deposit_neon_like_tokens_from_solana_to_neon(
            token_mint, new_sol_account, new_account, web3_client_usdt.chain_id, operator_keypair, amount
        )

        usdt_balance_after = web3_client_usdt.get_balance(new_account)
        assert usdt_balance_after == amount * 1000000000000

    @pytest.mark.multipletokens
    def test_transfer_wrapped_sol_token_from_solana_to_neon(self, solana_account, web3_client_sol, evm_loader):
        new_account = self.web3_client.create_account()

        amount = 0.1
        full_amount = int(amount * LAMPORT_PER_SOL)

        mint_pubkey = wSOL["address_spl"]
        ata_address = get_associated_token_address(solana_account.pubkey(), mint_pubkey)

        self.sol_client.create_associate_token_acc(solana_account, solana_account, mint_pubkey)

        # wrap SOL
        wrap_sol_tx = make_wSOL(full_amount, solana_account.pubkey(), ata_address)
        self.sol_client.send_tx_and_check_status_ok(wrap_sol_tx, solana_account)

        evm_loader.sent_token_from_solana_to_neon(
            solana_account,
            wSOL["address_spl"],
            new_account,
            full_amount,
            web3_client_sol.eth.chain_id,
        )

        assert web3_client_sol.get_balance(new_account) / LAMPORT_PER_SOL == full_amount


@allure.feature("Transfer NEON <-> Solana")
@allure.story("Withdraw from NEON to Solana")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestWithdraw:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def withdraw(self, sender_acc, dest_acc, move_amount, withdraw_contract):
        tx = self.web3_client.make_raw_tx(sender_acc, amount=move_amount)
        instruction_tx = withdraw_contract.functions.withdraw(bytes(dest_acc.pubkey())).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_acc, instruction_tx)
        assert receipt["status"] == 1

    @pytest.mark.parametrize("move_amount, error", [(11000, web3.exceptions.ContractLogicError), (10000, ValueError)])
    def test_failed_withdraw_insufficient_balance(
        self, pytestconfig: Config, move_amount, error, withdraw_contract, neon_mint, solana_account
    ):
        amount = move_amount * pow(10, 18)
        with pytest.raises(error):
            self.withdraw(self.accounts.create_account(10000), solana_account, amount, withdraw_contract)

    @pytest.mark.only_stands
    def test_success_withdraw_to_non_existing_account(
        self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        """Should successfully withdraw NEON tokens to previously non-existing Associated Token Account"""
        sender_account = self.accounts[0]
        dest_acc = Keypair()
        self.sol_client.request_airdrop(dest_acc.pubkey(), 1_000_000_000)
        spl_neon_token = SplToken(self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc)
        dest_token_acc = get_associated_token_address(dest_acc.pubkey(), neon_mint)
        move_amount = self.web3_client._web3.to_wei(5, "ether")

        self.withdraw(sender_account, dest_acc, move_amount, withdraw_contract)
        destination_balance_after = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))
        assert int(destination_balance_after.value.amount) == int(move_amount / 1_000_000_000)

    @pytest.mark.mainnet
    def test_success_withdraw_to_existing_account(
        self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        """Should successfully withdraw NEON tokens to existing Associated Token Account"""
        dest_acc = solana_account
        sender_account = self.accounts[0]

        wait_condition(lambda: self.sol_client.get_balance(dest_acc.pubkey()) != 0)

        trx = Transaction()
        trx.add(create_associated_token_account(dest_acc.pubkey(), dest_acc.pubkey(), neon_mint))
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.sol_client.send_transaction(trx, dest_acc, opts=opts)

        dest_token_acc = get_associated_token_address(dest_acc.pubkey(), neon_mint)

        move_amount_alan = 2_123_000_321_000_000_000
        move_amount_galan = int(move_amount_alan / 1_000_000_000)

        spl_neon_token = SplToken(self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc)

        destination_balance_before = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))

        self.withdraw(sender_account, dest_acc, move_amount_alan, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))
        assert int(destination_balance_after.value.amount) == move_amount_galan + int(
            destination_balance_before.value.amount
        )

    def test_failed_withdraw_non_divisible_amount(
        self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        sender_account = self.accounts[0]
        dest_acc = solana_account

        spl_neon_token = SplToken(self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc)

        move_amount = pow(10, 18) + 123

        destination_balance_before = spl_neon_token.get_balance(dest_acc.pubkey(), commitment=Commitment("confirmed"))
        with pytest.raises(AttributeError):
            _ = destination_balance_before.value

        with pytest.raises(web3_exceptions.ContractLogicError):
            self.withdraw(sender_account, dest_acc, move_amount, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(dest_acc.pubkey(), commitment=Commitment("confirmed"))
        with pytest.raises(AttributeError):
            _ = destination_balance_after.value
