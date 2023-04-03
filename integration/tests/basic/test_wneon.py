import random

import allure
import pytest
import web3
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature

from integration.tests.basic.helpers.basic import BaseMixin
from utils.helpers import wait_condition


@pytest.fixture(scope="session")
def wneon(web3_client, faucet):
    acc = web3_client.create_account()
    faucet.request_neon(acc.address, 100)

    contract, _ = web3_client.deploy_and_get_contract("WNEON", "0.4.26", account=acc)
    return contract


@allure.feature("Ethereum compatibility")
@allure.story("Wrapped NEON tests")
class TestWNeon(BaseMixin):
    SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

    def deposit(self, wneon, amount, acc):
        value = self.web3_client._web3.to_wei(amount, "ether")
        instruction_tx = wneon.functions.deposit().build_transaction(
            self.make_tx_object(acc, value)
        )
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
        neon_balance = self.get_balance_from_wei(address)
        wneon_balance = self.web3_client.from_wei(
            wneon.functions.balanceOf(address).call(), "ether"
        )
        return neon_balance, wneon_balance

    def test_deposit_and_total_supply(self, wneon):
        neon_balance_before, wneon_balance_before = self.get_balances(
            wneon, self.recipient_account.address
        )
        deposit_amount = random.randint(1, 100)
        receipt = self.deposit(wneon, deposit_amount, self.recipient_account)
        assert receipt["status"] == 1
        neon_balance_after, wneon_balance_after = self.get_balances(
            wneon, self.recipient_account.address
        )
        assert wneon_balance_after == deposit_amount
        assert neon_balance_before - deposit_amount - neon_balance_after < 0.2

        deposit_amount2 = random.randint(1, 100)
        self.deposit(wneon, deposit_amount2, self.sender_account)
        assert (
            self.web3_client._web3.from_wei(
                wneon.functions.totalSupply().call(), "ether"
            )
            == deposit_amount + deposit_amount2
        )

    def test_withdraw(self, wneon):
        deposit_amount = 100
        self.deposit(wneon, deposit_amount, self.recipient_account)
        neon_balance_before, wneon_balance_before = self.get_balances(
            wneon, self.recipient_account.address
        )
        withdraw_amount = random.randint(1, deposit_amount)
        instruction_tx = wneon.functions.withdraw(
            self.web3_client._web3.to_wei(withdraw_amount, "ether")
        ).build_transaction(self.make_tx_object(self.recipient_account))
        receipt = self.web3_client.send_transaction(
            self.recipient_account, instruction_tx
        )
        assert receipt["status"] == 1

        neon_balance_after, wneon_balance_after = self.get_balances(
            wneon, self.recipient_account.address
        )

        assert neon_balance_after - neon_balance_before - withdraw_amount < 0.2
        assert wneon_balance_after == wneon_balance_before - withdraw_amount

    def test_transfer_and_check_token_does_not_use_spl(self, wneon, new_account):
        deposit_amount = 100
        self.deposit(wneon, deposit_amount, self.sender_account)
        neon_balance_sender_before, wneon_balance_sender_before = self.get_balances(
            wneon, self.sender_account.address
        )

        transfer_amount = random.randint(1, deposit_amount)
        tx = self.make_tx_object(self.sender_account)
        instruction_tx = wneon.functions.transfer(
            new_account.address, self.web3_client._web3.to_wei(transfer_amount, "ether")
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1

        solana_trx = self.web3_client.get_solana_trx_by_neon(
            receipt["transactionHash"].hex()
        )
        wait_condition(
            lambda: self.sol_client.get_transaction(
                Signature.from_string(solana_trx["result"][0]),
            )
            != GetTransactionResp(None)
        )
        solana_resp = self.sol_client.get_transaction(
            Signature.from_string(solana_trx["result"][0])
        )
        sol_accounts = solana_resp.value.transaction.transaction.message.account_keys
        assert self.SPL_TOKEN_PROGRAM_ID not in sol_accounts

        neon_balance_sender_after, wneon_balance_sender_after = self.get_balances(
            wneon, self.sender_account.address
        )
        _, wneon_balance_recipient_after = self.get_balances(wneon, new_account.address)
        assert wneon_balance_recipient_after == transfer_amount
        assert (
            wneon_balance_sender_after == wneon_balance_sender_before - transfer_amount
        )
        assert neon_balance_sender_after - neon_balance_sender_before < 0.2

    def test_transfer_from(self, wneon, new_account):
        deposit_amount = 100
        self.deposit(wneon, deposit_amount, self.sender_account)
        neon_balance_sender_before, wneon_balance_sender_before = self.get_balances(
            wneon, self.sender_account.address
        )
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

        instruction_tx = wneon.functions.approve(
            new_account.address, transfer_amount_wei
        ).build_transaction(self.make_tx_object(self.sender_account))
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        assert receipt["status"] == 1
        instruction_tx = wneon.functions.transferFrom(
            self.sender_account.address, new_account.address, transfer_amount_wei
        ).build_transaction(self.make_tx_object(new_account))
        receipt = self.web3_client.send_transaction(new_account, instruction_tx)
        assert receipt["status"] == 1
        neon_balance_sender_after, wneon_balance_sender_after = self.get_balances(
            wneon, self.sender_account.address
        )
        neon_balance_recipient_after, wneon_balance_recipient_after = self.get_balances(
            wneon, new_account.address
        )
        assert (
            wneon_balance_recipient_after
            == wneon_balance_recipient_before + transfer_amount
        )
        assert (
            wneon_balance_sender_after == wneon_balance_sender_before - transfer_amount
        )
        assert neon_balance_sender_after - neon_balance_sender_before < 0.2
        assert neon_balance_recipient_after - neon_balance_recipient_before < 0.2
