import allure
import pytest
import web3

from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("Ethereum compatibility")
@allure.story("Basic tests for erc20_spl transfers")
class TestErc20SplTransfer(BaseMixin):

    @pytest.mark.parametrize("transfer_amount", [0, 1, 10, 100])
    def test_send_spl_wrapped_token_from_one_account_to_another(
            self, transfer_amount: int, erc20_spl
    ):
        """Send spl wrapped account from one account to another"""
        initial_spl_balance = erc20_spl.get_balance(self.recipient_account)
        initial_neon_balance = self.recipient_account_balance

        erc20_spl.transfer(erc20_spl.account, self.recipient_account, transfer_amount)

        # Spl balance
        assert erc20_spl.get_balance(self.recipient_account) == initial_spl_balance + transfer_amount

        # Neon balance
        self.assert_balance(
            self.recipient_account.address, initial_neon_balance, rnd_dig=3
        )

    def test_send_more_than_exist_on_account_spl(self, erc20_spl):
        """Send more than exist on account: spl (with different precision)"""

        transfer_amount = 1_000_000_000_000_000_000_000
        initial_spl_balance = erc20_spl.get_balance(self.recipient_account)
        initial_neon_balance = self.recipient_account_balance

        with pytest.raises(web3.exceptions.ContractLogicError):
            erc20_spl.transfer(erc20_spl.account, self.recipient_account, transfer_amount)

        # Spl balance
        assert erc20_spl.get_balance(self.recipient_account) == initial_spl_balance

        # Neon balance
        self.assert_balance(
            self.recipient_account.address, initial_neon_balance, rnd_dig=3
        )

    def test_send_negative_sum_from_account_spl(self, erc20_spl):
        """Send negative sum from account: spl (with different precision)"""

        transfer_amount = -1
        initial_spl_balance = erc20_spl.get_balance(self.recipient_account)
        initial_neon_balance = self.recipient_account_balance
        with pytest.raises(web3.exceptions.ValidationError):
            erc20_spl.transfer(erc20_spl.account, self.recipient_account.address, transfer_amount)

        # Spl balance
        assert erc20_spl.get_balance(self.recipient_account) == initial_spl_balance

        # Neon balance
        self.assert_balance(
            self.recipient_account.address, initial_neon_balance, rnd_dig=3
        )

    def test_send_tokens_to_non_exist_acc(self, erc20_spl):
        """Send tokens to non-existent in EVM account"""
        recipient = self.web3_client.eth.account.create()
        transfer_amount = 10

        initial_sender_spl_balance = erc20_spl.get_balance(erc20_spl.account)
        erc20_spl.transfer(erc20_spl.account, recipient.address, transfer_amount)

        # Spl balance
        assert erc20_spl.get_balance(recipient) == transfer_amount
        assert erc20_spl.get_balance(erc20_spl.account) == initial_sender_spl_balance - transfer_amount

        # Neon balance
        self.assert_balance(recipient.address, 0, rnd_dig=3)
