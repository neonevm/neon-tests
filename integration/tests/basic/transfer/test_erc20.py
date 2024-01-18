import allure
import pytest
import typing as tp

import web3

from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client
from integration.tests.basic.helpers.assert_message import AssertMessage

DEFAULT_ERC20_BALANCE = 1000


@allure.feature("Ethereum compatibility")
@allure.story("Basic tests for erc20 transfers")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestERC20Transfer:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("transfer_amount", [0, 1, 100])
    def test_send_erc20_token_from_one_account_to_another(self, erc20_simple, transfer_amount: tp.Union[int, float]):
        """Send erc20 token from one account to another"""
        recipient_account = self.accounts[1]

        initial_sender_neon_balance = self.web3_client.get_balance(erc20_simple.owner.address)
        initial_recipient_neon_balance = self.web3_client.get_balance(recipient_account)

        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)
        initial_recipient_erc20_balance = erc20_simple.get_balance(recipient_account)
        tx_receipt = erc20_simple.transfer(erc20_simple.owner, recipient_account, transfer_amount)
        # ERC20 balance
        assert (
            erc20_simple.get_balance(erc20_simple.owner) == initial_sender_erc20_balance - transfer_amount
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        assert self.web3_client.get_balance(erc20_simple.owner) == (
            initial_sender_neon_balance - self.web3_client.calculate_trx_gas(tx_receipt)
        )

        assert erc20_simple.get_balance(recipient_account) == transfer_amount + initial_recipient_erc20_balance
        assert initial_recipient_neon_balance == self.web3_client.get_balance(recipient_account)

    def test_send_more_than_exist_on_account_erc20(self, erc20_simple):
        """Send more than exist on account: ERC20"""

        recipient_account = self.accounts[1]

        initial_sender_neon_balance = self.web3_client.get_balance(erc20_simple.owner.address)
        initial_recipient_neon_balance = self.web3_client.get_balance(recipient_account)

        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)
        transfer_amount = erc20_simple.get_balance(erc20_simple.owner) + 1

        with pytest.raises(web3.exceptions.ContractLogicError):
            erc20_simple.transfer(erc20_simple.owner, recipient_account, transfer_amount)

        # ERC20 balance
        assert (
            erc20_simple.get_balance(erc20_simple.owner) == initial_sender_erc20_balance
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        # Neon balance
        assert initial_sender_neon_balance == self.web3_client.get_balance(erc20_simple.owner.address)
        assert initial_recipient_neon_balance == self.web3_client.get_balance(recipient_account)

    def test_send_token_to_self_erc20(self, erc20_simple):
        """Send token to self: ERC20"""

        transfer_amount = 10
        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)
        initial_sender_neon_balance = self.web3_client.get_balance(erc20_simple.owner.address)
        erc20_simple.transfer(erc20_simple.owner, erc20_simple.owner, transfer_amount)

        # ERC20 balance (now the balance is the same as before the transfer)
        assert (
            erc20_simple.get_balance(erc20_simple.owner) == initial_sender_erc20_balance
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        # Neon balance
        assert initial_sender_neon_balance > self.web3_client.get_balance(erc20_simple.owner.address)

    def test_send_tokens_to_non_exist_acc(self, erc20_simple):
        """Send tokens to non-existent in EVM account"""
        recipient = self.web3_client.eth.account.create()
        transfer_amount = 10

        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)
        initial_sender_neon_balance = self.web3_client.get_balance(erc20_simple.owner.address)

        erc20_simple.transfer(erc20_simple.owner, recipient, transfer_amount)

        assert (
            erc20_simple.get_balance(erc20_simple.owner) == initial_sender_erc20_balance - transfer_amount
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        assert erc20_simple.get_balance(recipient) == transfer_amount, AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        # Neon balance
        assert initial_sender_neon_balance > self.web3_client.get_balance(erc20_simple.owner.address)
