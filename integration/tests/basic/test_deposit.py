import json

import pytest
import allure
from _pytest.config import Config
from solana.publickey import PublicKey
from solana.keypair import Keypair
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
)
from web3 import exceptions as web3_exceptions

from integration.tests.basic.helpers.basic import BaseMixin, BaseTests
from utils.consts import LAMPORT_PER_SOL
from utils.transfers_inter_networks import neon_transfer_tx, wSOL_tx, neon_from_solana_to_neon_tx
from utils.helpers import wait_condition

wSOL = {
    "chain_id": 111,
    "address_spl": "So11111111111111111111111111111111111111112",
    "address": "0x16869acc45BA20abEFB2DdE2096F66373fDe364F",
    "decimals": 9,
    "name": "Wrapped SOL",
    "symbol": "wSOL",
    "logo_uri": "https://raw.githubusercontent.com/neonlabsorg/token-list/master/assets/solana-wsol-logo.svg",
}


@allure.feature("Transfer NEON <-> Solana")
@allure.story("Deposit from Solana to NEON")
class TestDeposit(BaseMixin):
    def withdraw_neon(self, dest_acc, move_amount):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "precompiled/NeonToken", "0.8.10", account=self.sender_account
        )

        instruction_tx = contract.functions.withdraw(
            bytes(dest_acc.public_key)
        ).build_transaction(
            {
                "from": self.sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.sender_account.address
                ),
                "gasPrice": self.web3_client.gas_price(),
                "value": self.web3_client._web3.to_wei(move_amount, "ether"),
            }
        )
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

    def create_ata(self, solana_account, neon_mint):
        trx = Transaction()
        trx.add(
            create_associated_token_account(
                solana_account.public_key, solana_account.public_key, neon_mint
            )
        )
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.sol_client.send_transaction(trx, solana_account, opts=opts)

    def send_tx_and_check_status_ok(self, tx, solana_account):
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        sig = self.sol_client.send_transaction(tx, solana_account, opts=opts).value
        sig_status = json.loads((self.sol_client.confirm_transaction(sig)).to_json())
        assert sig_status["result"]["value"][0]["status"] == {"Ok": None}, f"error:{sig_status}"

    def test_transfer_neon_from_solana_to_neon(
            self, new_account, solana_account, pytestconfig: Config, neon_mint
    ):
        """Transfer Neon from Solana -> Neon"""
        amount = 0.1
        full_amount = int(amount * LAMPORT_PER_SOL)
        evm_loader_id = pytestconfig.environment.evm_loader

        balance_pubkey = self.sol_client.ether2balance(new_account.address,
                                                       self.web3_client._chain_id,
                                                       evm_loader_id)

        neon_balance_before = self.get_balance_from_wei(new_account.address)

        self.create_ata(solana_account, neon_mint)
        self.withdraw_neon(solana_account, amount)
        tx = neon_from_solana_to_neon_tx(
            solana_account,
            balance_pubkey,
            neon_mint,
            new_account,
            full_amount,
            evm_loader_id,
            self.web3_client._chain_id
        )
        self.send_tx_and_check_status_ok(tx, solana_account)

        neon_balance_after = self.get_balance_from_wei(new_account.address)
        assert neon_balance_after == neon_balance_before + amount

    def test_transfer_spl_token_from_solana_to_neon(
            self, solana_account, new_account, pytestconfig: Config, erc20_spl
    ):
        evm_loader_id = pytestconfig.environment.evm_loader
        amount = 0.1
        full_amount = int(amount * LAMPORT_PER_SOL)

        mint_pubkey = PublicKey(wSOL["address_spl"])
        ata_address = get_associated_token_address(
            solana_account.public_key, mint_pubkey
        )

        self.create_ata(solana_account, mint_pubkey)

        spl_neon_token = SplToken(
            self.sol_client, mint_pubkey, TOKEN_PROGRAM_ID, solana_account
        )
        ata_balance_before = spl_neon_token.get_balance(
            ata_address, commitment=Commitment("confirmed")
        )

        # wrap SOL
        wrap_sol_tx = wSOL_tx(self.sol_client,
            wSOL, full_amount, solana_account.public_key, ata_address
        )
        self.send_tx_and_check_status_ok(wrap_sol_tx, solana_account)

        # transfer wSOL
        transfer_tx = neon_transfer_tx(
            self.web3_client,
            self.sol_client,
            full_amount,
            wSOL,
            solana_account,
            new_account,
            erc20_spl,
            evm_loader_id
        )
        self.send_tx_and_check_status_ok(transfer_tx, solana_account)

        ata_balance_after = spl_neon_token.get_balance(
            ata_address, commitment=Commitment("confirmed")
        )

        assert (
                int(ata_balance_after.value.amount)
                == int(ata_balance_before.value.amount) + full_amount
        )


@allure.feature("Transfer NEON <-> Solana")
@allure.story("Withdraw from NEON to Solana")
class TestWithdraw(BaseTests):
    def withdraw(self, dest_acc, move_amount, withdraw_contract):
        instruction_tx = withdraw_contract.functions.withdraw(
            bytes(dest_acc.public_key)
        ).build_transaction(
            {
                "from": self.acc.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.acc.address),
                "gasPrice": self.web3_client.gas_price(),
                "value": move_amount,
            }
        )
        receipt = self.web3_client.send_transaction(self.acc, instruction_tx)
        assert receipt["status"] == 1

    @pytest.mark.only_stands
    def test_success_withdraw_to_non_existing_account(
            self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        """Should successfully withdraw NEON tokens to previously non-existing Associated Token Account"""
        dest_acc = Keypair.generate()
        self.sol_client.request_airdrop(dest_acc.public_key, 1_000_000_000)

        spl_neon_token = SplToken(
            self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc
        )

        dest_token_acc = get_associated_token_address(dest_acc.public_key, neon_mint)

        move_amount = self.web3_client._web3.to_wei(5, "ether")

        destination_balance_before = spl_neon_token.get_balance(
            dest_acc.public_key, commitment=Commitment("confirmed")
        )
        with pytest.raises(AttributeError):
            _ = destination_balance_before.value

        self.withdraw(dest_acc, move_amount, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(
            dest_token_acc, commitment=Commitment("confirmed")
        )

        assert int(destination_balance_after.value.amount) == int(
            move_amount / 1_000_000_000
        )

    def test_success_withdraw_to_existing_account(
            self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        """Should successfully withdraw NEON tokens to existing Associated Token Account"""
        dest_acc = solana_account

        wait_condition(lambda: self.sol_client.get_balance(dest_acc.public_key) != 0)

        trx = Transaction()
        trx.add(
            create_associated_token_account(
                dest_acc.public_key, dest_acc.public_key, neon_mint
            )
        )
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.sol_client.send_transaction(trx, dest_acc, opts=opts)

        dest_token_acc = get_associated_token_address(dest_acc.public_key, neon_mint)

        move_amount_alan = 2_123_000_321_000_000_000
        move_amount_galan = int(move_amount_alan / 1_000_000_000)

        spl_neon_token = SplToken(
            self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc
        )

        destination_balance_before = spl_neon_token.get_balance(
            dest_token_acc, commitment=Commitment("confirmed")
        )
        assert int(destination_balance_before.value.amount) == 0

        self.withdraw(dest_acc, move_amount_alan, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(
            dest_token_acc, commitment=Commitment("confirmed")
        )
        assert int(destination_balance_after.value.amount) == move_amount_galan

    def test_failed_withdraw_non_divisible_amount(
            self, pytestconfig: Config, withdraw_contract, neon_mint, solana_account
    ):
        dest_acc = solana_account

        spl_neon_token = SplToken(
            self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc.public_key
        )

        move_amount = pow(10, 18) + 123

        destination_balance_before = spl_neon_token.get_balance(
            dest_acc.public_key, commitment=Commitment("confirmed")
        )
        with pytest.raises(AttributeError):
            _ = destination_balance_before.value

        with pytest.raises(web3_exceptions.ContractLogicError):
            self.withdraw(dest_acc, move_amount, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(
            dest_acc.public_key, commitment=Commitment("confirmed")
        )
        with pytest.raises(AttributeError):
            _ = destination_balance_after.value

    @pytest.mark.parametrize("move_amount", [11000, 10000])
    def test_failed_withdraw_insufficient_balance(
            self,
            pytestconfig: Config,
            move_amount,
            withdraw_contract,
            neon_mint,
            solana_account,
    ):
        dest_acc = solana_account

        spl_neon_token = SplToken(
            self.sol_client, neon_mint, TOKEN_PROGRAM_ID, dest_acc.public_key
        )

        amount = move_amount * pow(10, 18)

        destination_balance_before = spl_neon_token.get_balance(
            dest_acc.public_key, commitment=Commitment("confirmed")
        )
        with pytest.raises(AttributeError):
            _ = destination_balance_before.value

        with pytest.raises(ValueError):
            self.withdraw(dest_acc, amount, withdraw_contract)

        destination_balance_after = spl_neon_token.get_balance(
            dest_acc.public_key, commitment=Commitment("confirmed")
        )
        with pytest.raises(AttributeError):
            _ = destination_balance_after.value
