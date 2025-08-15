import random
import re

import allure
import pytest
from web3.exceptions import Web3RPCError

from integration.tests.basic.helpers.assert_message import ErrorMessage
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client
from utils.helpers import gen_hash_of_block

U64_MAX = 18_446_744_073_709_551_615

GAS_LIMIT_AND_PRICE_DATA = (
    [1, None, ErrorMessage.GAS_LIMIT_REACHED.value],
    [U64_MAX + 1, None, ErrorMessage.GAS_OVERFLOW.value],
    [
        35_000,
        U64_MAX + 1,
        ErrorMessage.INSUFFICIENT_FUNDS_FOR_TRANSFER.value,
    ],
    [1, (U64_MAX + 1), ErrorMessage.GAS_LIMIT_REACHED.value],
    [1_000, int((U64_MAX + 100) / 1_000), ErrorMessage.GAS_LIMIT_REACHED.value],
)


@allure.feature("Ethereum compatibility")
@allure.story("Verify transactions validation")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestTransactionsValidation:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("gas_limit,gas_price,expected_message", GAS_LIMIT_AND_PRICE_DATA)
    def test_generate_bad_sign(self, gas_limit, gas_price, expected_message):
        """Generate bad sign (when v, r, s over allowed size)
        Too low gas_limit
        Too high gas_limit > u64::max
        Too high gas_price > u64::max
        Too high gas_limit * gas_price > u64::max
        """

        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        initial_sender_balance = self.web3_client.get_balance(sender_account)
        initial_recipient_balance = self.web3_client.get_balance(recipient_account)

        with pytest.raises(Web3RPCError, match=expected_message):
            self.web3_client.send_neon(sender_account, recipient_account, amount=1, gas=gas_limit, gas_price=gas_price)

        assert initial_sender_balance == self.web3_client.get_balance(sender_account)
        assert initial_recipient_balance == self.web3_client.get_balance(recipient_account)

    def test_send_underpriced_transaction(self, json_rpc_client):
        """Check that transaction can't be sent if gas value is too small"""
        gas_price = random.randint(0, 10000)

        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]

        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=1, gas_price=gas_price, estimate_gas=True
        )
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.raw_transaction.hex()])
        pattern = str.format(ErrorMessage.TRANSACTION_UNDERPRICED.value, gas_price) + r" \d.*"
        assert re.match(pattern, response["error"]["message"])
        assert response["error"]["code"] == -32000

    def test_send_too_big_transaction(self, json_rpc_client):
        """Transaction size is too big"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=1, estimate_gas=True
        )
        transaction["data"] = gen_hash_of_block(1024 * 1024)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        params = [signed_tx.raw_transaction.hex()]
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", params)
        assert ErrorMessage.TOO_BIG_TRANSACTION.value in response["error"]["message"]
        assert response["error"]["code"] == -32000

    def test_big_memory_value(self):
        sender_account = self.accounts[0]
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/BigMemoryValue", "0.8.12", account=sender_account
        )
        bytes_amount = contract.functions.makeBigMemoryValue(5).call()
        assert bytes_amount == 32 * 1024

    def test_erc_1820_contract_call_transaction(self):
        """Check ERC-1820 transaction (without chain_id in sign)"""
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]

        initial_sender_balance = self.web3_client.get_balance(sender_account)
        initial_recipient_balance = self.web3_client.get_balance(recipient_account)

        transfer_amount = 100

        transaction = self.web3_client.make_raw_tx(
            from_=sender_account, to=recipient_account, amount=transfer_amount, chain_id=None, estimate_gas=True
        )
        resp = self.web3_client.send_transaction(sender_account, transaction)

        assert resp["status"] == 1, "Transaction status must be 0x1"

        assert self.web3_client.get_balance(sender_account.address) < (initial_sender_balance - transfer_amount)
        assert self.web3_client.get_balance(recipient_account.address) == (initial_recipient_balance + transfer_amount)

    def test_transaction_does_not_fail_nested_contract(self):
        """Send Neon to contract via low level call"""
        sender_account = self.accounts[0]
        _, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "issues/ndev1004/ContractOne", "0.8.15", account=sender_account
        )
        address = contract_deploy_tx["contractAddress"]

        contract_two, _ = self.web3_client.deploy_and_get_contract(
            "issues/ndev1004/ContractTwo", "0.8.15", account=sender_account
        )
        balance = contract_two.functions.getBalance().call()
        assert balance == 0
        contract_two.functions.depositOnContractOne(address).call()
