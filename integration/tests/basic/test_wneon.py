import random

import pytest
import web3
from solana.rpc.types import Commitment, TxOpts
from solana.transaction import Transaction
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
)

import allure
from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.solana_client import SolanaClient


@allure.feature("Ethereum compatibility")
@allure.story("Wrapped NEON tests")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestWNeon:
    SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def deposit(self, wneon, amount, acc):
        value = self.web3_client._web3.to_wei(amount, "ether")
        instruction_tx = wneon.functions.deposit().build_transaction(self.make_tx_object(acc, value))
        return self.web3_client.send_transaction(acc, instruction_tx)

    def make_tx_object(self, acc, value=None):
        tx = {
            "from": acc.address,
            "nonce": self.web3_client.eth.get_transaction_count(acc.address),
            "gasPrice": self.web3_client.gas_price(),
        }
        if value is not None:
            tx["value"] = value
        return tx

    def get_balances(self, wneon, address):
        neon_balance = self.web3_client.get_balance(address)
        wneon_balance = self.web3_client.from_wei(wneon.functions.balanceOf(address).call(), "ether")
        return neon_balance, wneon_balance

    def test_deposit_and_total_supply(self, wneon):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        neon_balance_before, wneon_balance_before = self.get_balances(wneon, recipient_account.address)
        deposit_amount = random.randint(1, 100)
        receipt = self.deposit(wneon, deposit_amount, recipient_account)
        assert receipt["status"] == 1
        neon_balance_after, wneon_balance_after = self.get_balances(wneon, recipient_account.address)
        assert wneon_balance_after == deposit_amount
        assert neon_balance_before - deposit_amount - neon_balance_after < 1

        deposit_amount2 = random.randint(1, 100)
        self.deposit(wneon, deposit_amount2, sender_account)
        assert (
            self.web3_client._web3.from_wei(wneon.functions.totalSupply().call(), "ether")
            == deposit_amount + deposit_amount2
        )

    def test_withdraw(self, wneon):
        deposit_amount = 100
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(wneon, deposit_amount, recipient_account)
        neon_balance_before, wneon_balance_before = self.get_balances(wneon, recipient_account.address)
        withdraw_amount = random.randint(1, deposit_amount)
        instruction_tx = wneon.functions.withdraw(
            self.web3_client._web3.to_wei(withdraw_amount, "ether")
        ).build_transaction(self.make_tx_object(recipient_account))
        receipt = self.web3_client.send_transaction(recipient_account, instruction_tx)
        assert receipt["status"] == 1

        neon_balance_after, wneon_balance_after = self.get_balances(wneon, recipient_account.address)

        assert neon_balance_after - neon_balance_before - withdraw_amount < 0.2
        assert wneon_balance_after == wneon_balance_before - withdraw_amount

    def test_transfer_and_check_token_does_not_use_spl(self, wneon, new_account):
        deposit_amount = 100
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(wneon, deposit_amount, sender_account)
        neon_balance_sender_before, wneon_balance_sender_before = self.get_balances(wneon, sender_account.address)

        transfer_amount = random.randint(1, deposit_amount)
        tx = self.make_tx_object(sender_account)
        instruction_tx = wneon.functions.transfer(
            new_account.address, self.web3_client._web3.to_wei(transfer_amount, "ether")
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1

        solana_trx = self.web3_client.get_solana_trx_by_neon(receipt["transactionHash"].hex())
        wait_condition(
            lambda: self.sol_client.get_transaction(
                Signature.from_string(solana_trx["result"][0]),
            )
            != GetTransactionResp(None),
            timeout_sec=30,
        )
        solana_resp = self.sol_client.get_transaction(Signature.from_string(solana_trx["result"][0]))
        sol_accounts = solana_resp.value.transaction.transaction.message.account_keys
        assert self.SPL_TOKEN_PROGRAM_ID not in sol_accounts

        neon_balance_sender_after, wneon_balance_sender_after = self.get_balances(wneon, sender_account.address)
        _, wneon_balance_recipient_after = self.get_balances(wneon, new_account.address)
        assert wneon_balance_recipient_after == transfer_amount
        assert wneon_balance_sender_after == wneon_balance_sender_before - transfer_amount
        assert neon_balance_sender_after - neon_balance_sender_before < 0.2

    def test_transfer_from(self, wneon, new_account):
        deposit_amount = 100
        sender_account = self.accounts[0]
        self.deposit(wneon, deposit_amount, sender_account)
        neon_balance_sender_before, wneon_balance_sender_before = self.get_balances(wneon, sender_account.address)
        (
            neon_balance_recipient_before,
            wneon_balance_recipient_before,
        ) = self.get_balances(wneon, new_account.address)
        transfer_amount = random.randint(1, 100)
        transfer_amount_wei = self.web3_client._web3.to_wei(transfer_amount, "ether")

        with pytest.raises(web3.exceptions.ContractLogicError):
            wneon.functions.transferFrom(
                self.sender_account.address, new_account.address, transfer_amount_wei
            ).build_transaction(self.make_tx_object(new_account))

        instruction_tx = wneon.functions.approve(new_account.address, transfer_amount_wei).build_transaction(
            self.make_tx_object(sender_account)
        )
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        instruction_tx = wneon.functions.transferFrom(
            sender_account.address, new_account.address, transfer_amount_wei
        ).build_transaction(self.make_tx_object(new_account))
        receipt = self.web3_client.send_transaction(new_account, instruction_tx)
        assert receipt["status"] == 1
        neon_balance_sender_after, wneon_balance_sender_after = self.get_balances(wneon, sender_account.address)
        neon_balance_recipient_after, wneon_balance_recipient_after = self.get_balances(wneon, new_account.address)
        assert wneon_balance_recipient_after == wneon_balance_recipient_before + transfer_amount
        assert wneon_balance_sender_after == wneon_balance_sender_before - transfer_amount
        assert neon_balance_sender_after - neon_balance_sender_before < 0.2
        assert neon_balance_recipient_after - neon_balance_recipient_before < 0.2

    def test_withdraw_wneon_from_neon_to_solana(self, wneon, neon_mint, solana_account, withdraw_contract):
        deposit_amount = 100
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        self.deposit(wneon, deposit_amount, recipient_account)

        withdraw_amount = 5
        full_amount = self.web3_client._web3.to_wei(withdraw_amount, "ether")

        neon_balance_before, wneon_balance_before = self.get_balances(wneon, recipient_account.address)

        instruction_tx = wneon.functions.withdraw(full_amount).build_transaction(self.make_tx_object(recipient_account))

        receipt = self.web3_client.send_transaction(recipient_account, instruction_tx)
        assert receipt["status"] == 1

        neon_balance_after, wneon_balance_after = self.get_balances(wneon, recipient_account.address)

        assert wneon_balance_after == wneon_balance_before - withdraw_amount
        assert neon_balance_after - neon_balance_before < withdraw_amount

        wait_condition(lambda: self.sol_client.get_balance(solana_account.public_key) != 0)

        trx = Transaction()
        trx.add(create_associated_token_account(solana_account.public_key, solana_account.public_key, neon_mint))
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.sol_client.send_transaction(trx, solana_account, opts=opts)

        dest_token_acc = get_associated_token_address(solana_account.public_key, neon_mint)

        spl_neon_token = SplToken(self.sol_client, neon_mint, TOKEN_PROGRAM_ID, solana_account)

        destination_balance_before = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))
        neon_balance_before, wneon_balance_before = self.get_balances(wneon, recipient_account.address)

        instruction_tx = withdraw_contract.functions.withdraw(
            bytes(solana_account.public_key),
        ).build_transaction(
            {
                "from": recipient_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(recipient_account.address),
                "gasPrice": self.web3_client.gas_price(),
                "value": self.web3_client._web3.to_wei(withdraw_amount, "ether"),
            }
        )

        receipt = self.web3_client.send_transaction(recipient_account, instruction_tx)
        assert receipt["status"] == 1

        destination_balance_after = spl_neon_token.get_balance(dest_token_acc, commitment=Commitment("confirmed"))
        neon_balance_after, wneon_balance_after = self.get_balances(wneon, recipient_account.address)

        assert (
            int(destination_balance_after.value.amount)
            == int(destination_balance_before.value.amount) + full_amount / 1_000_000_000
        )
        assert wneon_balance_after == wneon_balance_before
        assert neon_balance_after - neon_balance_before < withdraw_amount
