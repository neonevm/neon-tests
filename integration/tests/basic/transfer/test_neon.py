import typing as tp

import pytest
import allure
from integration.tests.basic.helpers.assert_message import ErrorMessage
from utils.consts import Unit
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts


@allure.feature("Ethereum compatibility")
@allure.story("Basic tests for neon transfers")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestNeonTransfer:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("transfer_amount", [0, 0.1, 1, 0.000000001])
    def test_send_neon_from_one_account_to_another(self, transfer_amount: tp.Union[int, float]):
        """Send neon from one account to another"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        initial_sender_balance = self.web3_client.get_balance(sender_account)
        initial_recipient_balance = self.web3_client.get_balance(recipient_account)
        self.web3_client.send_neon(sender_account, recipient_account, transfer_amount)
        assert self.web3_client.get_balance(sender_account) < (
            initial_sender_balance - self.web3_client._web3.to_wei(transfer_amount, Unit.ETHER.value)
        )
        assert self.web3_client.get_balance(recipient_account.address) == (
            initial_recipient_balance + self.web3_client._web3.to_wei(transfer_amount, Unit.ETHER.value)
        )

    def test_send_more_than_exist_on_account_neon(self):
        """Send more than exist on account: neon"""
        amount = 11_000_501
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        sender_balance = self.web3_client.get_balance(sender_account)
        recipient_balance = self.web3_client.get_balance(recipient_account)

        with pytest.raises(Exception, match=ErrorMessage.INSUFFICIENT_FUNDS.value):
            self.web3_client.send_neon(sender_account, recipient_account, amount)

        assert sender_balance == self.web3_client.get_balance(sender_account)
        assert recipient_balance == self.web3_client.get_balance(recipient_account)

    def test_there_are_not_enough_neons_for_gas_fee(self):
        """There are not enough Neons for gas fee"""
        sender_account = self.accounts[0]
        recipient_account = self.web3_client.create_account()
        sender_balance = self.web3_client.get_balance(sender_account, Unit.ETHER)

        with pytest.raises(Exception, match=ErrorMessage.INSUFFICIENT_FUNDS.value):
            self.web3_client.send_neon(sender_account, recipient_account, amount=sender_balance)

        assert sender_balance == self.web3_client.get_balance(sender_account, Unit.ETHER)
        assert self.web3_client.get_balance(recipient_account) == 0

    def test_send_token_to_self_neon(self):
        """Send token to self"""
        sender_account = self.accounts[0]
        sender_balance = self.web3_client.get_balance(sender_account)

        self.web3_client.send_neon(sender_account, sender_balance, amount=1)
        assert sender_balance > self.web3_client.get_balance(sender_account)

    def test_erc_1820_transaction(self, json_rpc_client):
        """Check ERC-1820 transaction (without chain_id in sign)"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]

        initial_sender_balance = self.web3_client.get_balance(sender_account)
        initial_recipient_balance = self.web3_client.get_balance(recipient_account)

        transfer_amount = self.web3_client._web3.to_wei(2, Unit.ETHER.value)

        transaction = self.web3_client._make_tx_object(
            from_=sender_account, to=recipient_account, amount=transfer_amount
        )
        del transaction["chainId"]

        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)

        params = [signed_tx.rawTransaction.hex()]
        transaction = json_rpc_client.send_rpc("eth_sendRawTransaction", params)["result"]

        actual_result = self.web3_client._web3.eth.wait_for_transaction_receipt(transaction)

        assert actual_result["status"] == 1, "Transaction status must be 0x1"

        assert self.web3_client.get_balance(sender_account.address) < (initial_sender_balance - transfer_amount)
        assert self.web3_client.get_balance(recipient_account.address) == (initial_recipient_balance + transfer_amount)

    def test_transaction_does_not_fail_nested_contract(self):
        """Send Neon to contract via low level call"""
        sender_account = self.accounts[0]
        _, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "issues/ndev1004/ContractOne", "0.8.15", account=sender_account
        )
        address = contract_deploy_tx["contractAddress"]

        contractTwo, _ = self.web3_client.deploy_and_get_contract(
            "issues/ndev1004/ContractTwo", "0.8.15", account=sender_account
        )
        balance = contractTwo.functions.getBalance().call()
        assert balance == 0
        contractTwo.functions.depositOnContractOne(address).call()
