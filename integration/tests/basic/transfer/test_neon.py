import typing as tp

import pytest
import web3
import web3.exceptions

import allure
from integration.tests.basic.helpers.assert_message import ErrorMessage
from integration.tests.basic.helpers.basic import AccountData, BaseMixin
from utils.consts import InputTestConstants
from utils.helpers import gen_hash_of_block


@allure.feature("Ethereum compatibility")
@allure.story("Basic tests for neon transfers")
class TestNeonTransfer(BaseMixin):
    @pytest.mark.parametrize("transfer_amount", [0, 0.1, 1, 1.1])
    def test_send_neon_from_one_account_to_another(
            self, transfer_amount: tp.Union[int, float]
    ):
        """Send neon from one account to another"""
        initial_sender_balance = self.get_balance_from_wei(self.sender_account.address)
        initial_recipient_balance = self.get_balance_from_wei(
            self.recipient_account.address
        )
        self.send_neon(self.sender_account, self.recipient_account, transfer_amount)
        assert self.get_balance_from_wei(self.sender_account.address) < (
                initial_sender_balance - transfer_amount
        )
        assert self.get_balance_from_wei(self.recipient_account.address) == (
                initial_recipient_balance + transfer_amount
        )

    def test_send_more_than_exist_on_account_neon(self):
        """Send more than exist on account: neon"""
        amount = 11_000_501
        sender_balance, recipient_balance = (
            self.sender_account_balance,
            self.recipient_account_balance,
        )
        self.send_neon_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value,
        )

        self.assert_balance(self.sender_account.address, sender_balance, rnd_dig=1)
        self.assert_balance(
            self.recipient_account.address, recipient_balance, rnd_dig=1
        )

    def test_there_are_not_enough_neons_for_gas_fee(self):
        """There are not enough Neons for gas fee"""
        sender_amount = 1
        sender_account = self.create_account_with_balance(sender_amount)
        recipient_account = self.web3_client.create_account()

        self.send_neon_with_failure(
            sender_account=sender_account,
            recipient_account=recipient_account,
            amount=sender_amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value,
        )

        self.assert_balance(sender_account.address, sender_amount)
        self.assert_balance(recipient_account.address, 0)

    def test_send_token_to_self_neon(self):
        """Send token to self: Neon"""
        transfer_amount = 2
        balance_before = self.sender_account_balance

        self.send_neon(self.sender_account, self.sender_account, transfer_amount)
        self.assert_balance_less(
            self.sender_account.address,
            balance_before,
        )

    def test_send_token_to_an_invalid_address(self):
        """Send token to an invalid and not-existing address"""
        balance_before = self.sender_account_balance
        invalid_account = AccountData(address=gen_hash_of_block(20))
        self.send_neon_with_failure(
            sender_account=self.sender_account,
            recipient_account=invalid_account,
            amount=InputTestConstants.DEFAULT_TRANSFER_AMOUNT.value,
            exception=web3.exceptions.InvalidAddress,
        )

        balance_after = self.sender_account_balance
        assert balance_before == balance_after

    def test_erc_1820_transaction(self):
        """Check ERC-1820 transaction (without chain_id in sign)"""

        amount = 100
        sender_account = self.create_account_with_balance(amount)
        recipient_account = self.create_account_with_balance()
        transfer_amount = 2

        transaction = self.create_tx_object(
            sender=sender_account.address,
            recipient=recipient_account.address,
            amount=transfer_amount,
        )
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, sender_account.key
        )

        params = [signed_tx.rawTransaction.hex()]
        transaction = self.proxy_api.send_rpc("eth_sendRawTransaction", params)[
            "result"
        ]

        self.wait_transaction_accepted(transaction)
        actual_result = self.proxy_api.send_rpc(
            "eth_getTransactionReceipt", [transaction]
        )

        assert (
                actual_result["result"]["status"] == "0x1"
        ), "Transaction status must be 0x1"

        self.assert_balance(sender_account.address, amount - transfer_amount)
        self.assert_balance(
            recipient_account.address,
            InputTestConstants.FAUCET_1ST_REQUEST_AMOUNT.value + transfer_amount,
        )

    def test_transaction_does_not_fail_nested_contract(self):
        """Send Neon to contract via low level call"""
        _, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "issues/ndev1004/ContractOne", "0.8.15", account=self.sender_account
        )
        address = contract_deploy_tx["contractAddress"]

        contractTwo, _ = self.web3_client.deploy_and_get_contract(
            "issues/ndev1004/ContractTwo", "0.8.15", account=self.sender_account
        )
        balance = contractTwo.functions.getBalance().call()
        assert balance == 0
        contractTwo.functions.depositOnContractOne(address).call()
