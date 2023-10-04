import allure
import pytest
import typing as tp

import web3

from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin

DEFAULT_ERC20_BALANCE = 1000


@allure.feature("Ethereum compatibility")
@allure.story("Basic tests for erc20 transfers")
class TestErc20Transfer(BaseMixin):

    @pytest.mark.parametrize("transfer_amount", [0, 1, 10, 100])
    def test_send_erc20_token_from_one_account_to_another(
            self, erc20_simple, transfer_amount: tp.Union[int, float]
    ):
        """Send erc20 token from one account to another"""

        initial_sender_neon_balance, initial_recipient_neon_balance = (
            self.get_balance_from_wei(erc20_simple.owner.address),
            self.recipient_account_balance,
        )
        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)
        initial_recipient_erc20_balance = erc20_simple.get_balance(self.recipient_account)
        tx_receipt = erc20_simple.transfer(erc20_simple.owner, self.recipient_account, transfer_amount)
        # ERC20 balance
        assert (erc20_simple.get_balance(erc20_simple.owner)
                == initial_sender_erc20_balance - transfer_amount
                ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        self.assert_balance_less(
            erc20_simple.owner.address,
            initial_sender_neon_balance - self.calculate_trx_gas(tx_receipt=tx_receipt),
        )
        assert erc20_simple.get_balance(self.recipient_account) == transfer_amount + initial_recipient_erc20_balance
        assert initial_sender_neon_balance > self.get_balance_from_wei(
            erc20_simple.owner.address
        )
        assert initial_recipient_neon_balance == self.get_balance_from_wei(
            self.recipient_account.address
        )

    def test_send_more_than_exist_on_account_erc20(self, erc20_simple):
        """Send more than exist on account: ERC20"""

        initial_sender_neon_balance, initial_recipient_neon_balance = (
            self.get_balance_from_wei(erc20_simple.owner.address),
            self.recipient_account_balance,
        )
        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)
        transfer_amount = erc20_simple.get_balance(erc20_simple.owner) + 1
        with pytest.raises(web3.exceptions.ContractLogicError):
            erc20_simple.transfer(erc20_simple.owner, self.recipient_account, transfer_amount)

        # ERC20 balance
        assert erc20_simple.get_balance(
            erc20_simple.owner) == initial_sender_erc20_balance, AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        # Neon balance
        self.assert_balance(
            erc20_simple.owner.address,
            initial_sender_neon_balance,
            rnd_dig=0,
        )
        self.assert_balance(
            self.recipient_account.address, initial_recipient_neon_balance, rnd_dig=3
        )

    def test_send_negative_sum_from_account_erc20(self, erc20_simple):
        """Send negative sum from account: ERC20"""

        initial_sender_neon_balance, initial_recipient_neon_balance = (
            self.get_balance_from_wei(erc20_simple.owner.address),
            self.recipient_account_balance,
        )

        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)

        with pytest.raises(web3.exceptions.ValidationError):
            erc20_simple.transfer(erc20_simple.owner, self.recipient_account, -1)

        # ERC20 balance
        assert erc20_simple.get_balance(
            erc20_simple.owner) == initial_sender_erc20_balance, AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        # Neon balance
        self.assert_balance(
            erc20_simple.owner.address,
            initial_sender_neon_balance,
            rnd_dig=0,
        )
        self.assert_balance(
            self.recipient_account.address, initial_recipient_neon_balance, rnd_dig=3
        )

    def test_send_token_to_self_erc20(self, erc20_simple):
        """Send token to self: ERC20"""

        transfer_amount = 10
        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)

        initial_sender_neon_balance = self.get_balance_from_wei(erc20_simple.owner.address)
        erc20_simple.transfer(erc20_simple.owner, erc20_simple.owner, transfer_amount)

        # ERC20 balance (now the balance is the same as before the transfer)
        assert erc20_simple.get_balance(erc20_simple.owner) == initial_sender_erc20_balance, \
            AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        # Neon balance
        assert initial_sender_neon_balance > self.get_balance_from_wei(
            erc20_simple.owner.address
        )

    def test_send_tokens_to_non_exist_acc(self, erc20_simple):
        """Send tokens to non-existent in EVM account"""
        recipient = self.web3_client.eth.account.create()
        transfer_amount = 10

        initial_sender_neon_balance = self.sender_account_balance
        initial_sender_erc20_balance = erc20_simple.get_balance(erc20_simple.owner)
        erc20_simple.transfer(erc20_simple.owner, recipient, transfer_amount)

        assert erc20_simple.get_balance(
            erc20_simple.owner) == initial_sender_erc20_balance - transfer_amount, \
            AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        assert erc20_simple.get_balance(recipient) == transfer_amount, \
            AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        # Neon balance
        assert initial_sender_neon_balance > self.get_balance_from_wei(
            erc20_simple.owner.address
        )
