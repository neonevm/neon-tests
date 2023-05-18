import pytest
from _pytest.config import Config
from solana.keypair import Keypair
from solana.rpc.types import Commitment, TxOpts
from solana.transaction import Transaction
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (create_associated_token_account,
                                    get_associated_token_address)
from web3 import exceptions as web3_exceptions

import allure
from utils.helpers import wait_condition

from ..base import BaseTests


@allure.story("Withdraw tests")
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
