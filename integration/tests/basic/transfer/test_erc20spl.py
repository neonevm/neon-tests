import allure
import pytest
import web3

from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from integration.tests.basic.helpers.assert_message import AssertMessage


@allure.feature("Ethereum compatibility")
@allure.story("Basic tests for erc20_spl transfers")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestErc20SplTransfer:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("transfer_amount", [0, 1, 100])
    def test_send_spl_wrapped_token_from_one_account_to_another(self, transfer_amount: int, erc20_spl):
        """Send spl wrapped account from one account to another"""
        recipient_account = self.accounts[1]

        initial_sender_neon_balance = self.web3_client.get_balance(erc20_spl.account)
        initial_recipient_neon_balance = self.web3_client.get_balance(recipient_account)

        initial_sender_erc20_balance = erc20_spl.get_balance(erc20_spl.account)
        initial_recipient_erc20_balance = erc20_spl.get_balance(recipient_account)
        tx_receipt = erc20_spl.transfer(erc20_spl.account, recipient_account, transfer_amount)
        # ERC20 balance
        assert (
            erc20_spl.get_balance(erc20_spl.account) == initial_sender_erc20_balance - transfer_amount
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        assert self.web3_client.get_balance(erc20_spl.account) == (
            initial_sender_neon_balance - self.web3_client.calculate_trx_gas(tx_receipt)
        )

        assert erc20_spl.get_balance(recipient_account) == transfer_amount + initial_recipient_erc20_balance
        assert initial_recipient_neon_balance == self.web3_client.get_balance(recipient_account)

    def test_send_more_than_exist_on_account_spl(self, erc20_spl):
        """Send more than exist on account: spl (with different precision)"""

        recipient_account = self.accounts[1]

        initial_sender_neon_balance = self.web3_client.get_balance(erc20_spl.account.address)
        initial_recipient_neon_balance = self.web3_client.get_balance(recipient_account)

        initial_sender_erc20_balance = erc20_spl.get_balance(erc20_spl.account)
        transfer_amount = erc20_spl.get_balance(erc20_spl.account) + 1

        with pytest.raises(web3.exceptions.ContractLogicError):
            erc20_spl.transfer(erc20_spl.account, recipient_account, transfer_amount)

        # ERC20 balance
        assert (
            erc20_spl.get_balance(erc20_spl.account) == initial_sender_erc20_balance
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        # Neon balance
        assert initial_sender_neon_balance == self.web3_client.get_balance(erc20_spl.account.address)
        assert initial_recipient_neon_balance == self.web3_client.get_balance(recipient_account)

    def test_send_tokens_to_non_exist_acc(self, erc20_spl):
        """Send tokens to non-existent in EVM account"""
        recipient = self.web3_client.eth.account.create()
        transfer_amount = 10

        initial_sender_erc20_balance = erc20_spl.get_balance(erc20_spl.account)
        initial_sender_neon_balance = self.web3_client.get_balance(erc20_spl.account.address)

        erc20_spl.transfer(erc20_spl.account, recipient, transfer_amount)

        assert (
            erc20_spl.get_balance(erc20_spl.account) == initial_sender_erc20_balance - transfer_amount
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        assert erc20_spl.get_balance(recipient) == transfer_amount, AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        # Neon balance
        assert initial_sender_neon_balance > self.web3_client.get_balance(erc20_spl.account.address)
