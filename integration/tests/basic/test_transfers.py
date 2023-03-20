import random
import re
import typing as tp

import allure
import eth_utils
import pytest
import web3
import web3.exceptions

from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin, AccountData
from integration.tests.basic.helpers.assert_message import ErrorMessage
from utils.consts import InputTestConstants
from utils.helpers import gen_hash_of_block

U64_MAX = 18_446_744_073_709_551_615
DEFAULT_ERC20_BALANCE = 1000

GAS_LIMIT_AND_PRICE_DATA = (
    [1, None, ErrorMessage.GAS_LIMIT_REACHED.value],
    [U64_MAX + 1, None, ErrorMessage.GAS_OVERFLOW.value],
    [
        0,
        U64_MAX + 1,
        ErrorMessage.INSUFFICIENT_FUNDS.value,
    ],
    [1, (U64_MAX + 1), ErrorMessage.GAS_LIMIT_REACHED.value],
    [1_000, int((U64_MAX + 100) / 1_000), ErrorMessage.GAS_LIMIT_REACHED.value],
)


@allure.story("Basic tests for transfers")
class TestTransfer(BaseMixin):
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

    @pytest.mark.parametrize("transfer_amount", [0, 1, 10, 100])
    def test_send_erc20_token_from_one_account_to_another(
        self, transfer_amount: tp.Union[int, float]
    ):
        """Send erc20 token from one account to another"""

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20/ERC20.sol",
            "0.8.8",
            self.sender_account,
            contract_name="ERC20",
            constructor_args=["Test Token", "TT", DEFAULT_ERC20_BALANCE],
        )

        assert (
            contract.functions.balanceOf(self.sender_account.address).call()
            == DEFAULT_ERC20_BALANCE
        )
        initial_sender_neon_balance, initial_recipient_neon_balance = (
            self.sender_account_balance,
            self.recipient_account_balance,
        )

        tx_receipt = self.web3_client.send_erc20(
            self.sender_account,
            self.recipient_account.address,
            transfer_amount,
            contract_deploy_tx["contractAddress"],
            abi=contract.abi,
        )
        self.wait_transaction_accepted(tx_receipt.transactionHash.hex())
        # ERC20 balance
        assert (
            contract.functions.balanceOf(self.sender_account.address).call()
            == DEFAULT_ERC20_BALANCE - transfer_amount
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        self.assert_balance_less(
            self.sender_account.address,
            initial_sender_neon_balance - self.calculate_trx_gas(tx_receipt=tx_receipt),
        )
        assert initial_sender_neon_balance > self.get_balance_from_wei(
            self.sender_account.address
        )
        assert initial_recipient_neon_balance == self.get_balance_from_wei(
            self.recipient_account.address
        )

    @pytest.mark.parametrize("transfer_amount", [0, 1, 10, 100])
    def test_send_spl_wrapped_token_from_one_account_to_another(
        self, transfer_amount: int, erc20_spl
    ):
        """Send spl wrapped account from one account to another"""
        initial_spl_balance = erc20_spl.contract.functions.balanceOf(
            self.recipient_account.address
        ).call()
        initial_neon_balance = self.recipient_account_balance

        self.web3_client.send_erc20(
            erc20_spl.account,
            self.recipient_account,
            transfer_amount,
            erc20_spl.contract.address,
            abi=erc20_spl.contract.abi,
        )

        # Spl balance
        assert (
            erc20_spl.contract.functions.balanceOf(
                self.recipient_account.address
            ).call()
            == initial_spl_balance + transfer_amount
        )

        # Neon balance
        self.assert_balance(
            self.recipient_account.address, initial_neon_balance, rnd_dig=3
        )

    @pytest.mark.parametrize("amount", [11_000_501, 10_000_000.1])
    def test_send_more_than_exist_on_account_neon(self, amount: tp.Union[int, float]):
        """Send more than exist on account: neon"""

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

    def test_send_more_than_exist_on_account_spl(self, erc20_spl):
        """Send more than exist on account: spl (with different precision)"""

        transfer_amount = 1_000_000_000_000_000_000_000
        initial_spl_balance = erc20_spl.contract.functions.balanceOf(
            self.recipient_account.address
        ).call()
        initial_neon_balance = self.recipient_account_balance

        with pytest.raises(web3.exceptions.ContractLogicError):
            self.web3_client.send_erc20(
                erc20_spl.account,
                self.recipient_account,
                transfer_amount,
                erc20_spl.contract.address,
                abi=erc20_spl.contract.abi,
            )

        # Spl balance
        assert (
            erc20_spl.contract.functions.balanceOf(
                self.recipient_account.address
            ).call()
            == initial_spl_balance
        )

        # Neon balance
        self.assert_balance(
            self.recipient_account.address, initial_neon_balance, rnd_dig=3
        )

    def test_send_more_than_exist_on_account_erc20(self):
        """Send more than exist on account: ERC20"""

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20/ERC20.sol",
            "0.8.8",
            self.sender_account,
            contract_name="ERC20",
            constructor_args=["Test Token", "TT", DEFAULT_ERC20_BALANCE],
        )
        assert (
            contract.functions.balanceOf(self.sender_account.address).call()
            == DEFAULT_ERC20_BALANCE
        )
        initial_sender_neon_balance, initial_recipient_neon_balance = (
            self.sender_account_balance,
            self.recipient_account_balance,
        )

        with pytest.raises(web3.exceptions.ContractLogicError):
            self.web3_client.send_erc20(
                self.sender_account,
                self.recipient_account.address,
                100_000,
                contract_deploy_tx["contractAddress"],
                abi=contract.abi,
            )

        # ERC20 balance
        assert (
            contract.functions.balanceOf(self.sender_account.address).call()
            == DEFAULT_ERC20_BALANCE
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        # Neon balance
        self.assert_balance(
            self.sender_account.address,
            initial_sender_neon_balance,
            rnd_dig=0,
        )
        self.assert_balance(
            self.recipient_account.address, initial_recipient_neon_balance, rnd_dig=3
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

    def test_there_are_not_enough_neons_for_transfer(self):
        """There are not enough Neons for transfer"""
        sender_amount = 1
        sender_account = self.create_account_with_balance(sender_amount)
        recipient_account = self.web3_client.create_account()
        amount = 1.1

        self.send_neon_with_failure(
            sender_account=sender_account,
            recipient_account=recipient_account,
            amount=amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value,
        )

        self.assert_balance(sender_account.address, sender_amount)
        self.assert_balance(recipient_account.address, 0)

    def test_send_negative_sum_from_account_neon(self):
        """Send negative sum from account: neon"""

        sender_balance, recipient_balance = (
            self.sender_account_balance,
            self.recipient_account_balance,
        )

        self.send_neon_with_failure(
            sender_account=self.sender_account,
            recipient_account=self.recipient_account,
            amount=InputTestConstants.NEGATIVE_AMOUNT.value,
            error_message=ErrorMessage.NEGATIVE_VALUE.value,
        )

        self.assert_balance(self.sender_account.address, sender_balance, rnd_dig=0)
        self.assert_balance(
            self.recipient_account.address, recipient_balance, rnd_dig=1
        )

    def test_send_negative_sum_from_account_spl(self, erc20_spl):
        """Send negative sum from account: spl (with different precision)"""

        transfer_amount = -1
        initial_spl_balance = erc20_spl.contract.functions.balanceOf(
            self.recipient_account.address
        ).call()
        initial_neon_balance = self.recipient_account_balance

        with pytest.raises(web3.exceptions.ValidationError):
            self.web3_client.send_erc20(
                erc20_spl.account,
                self.recipient_account,
                transfer_amount,
                erc20_spl.contract.address,
                abi=erc20_spl.contract.abi,
            )

        # Spl balance
        assert (
            erc20_spl.contract.functions.balanceOf(
                self.recipient_account.address
            ).call()
            == initial_spl_balance
        )

        # Neon balance
        self.assert_balance(
            self.recipient_account.address, initial_neon_balance, rnd_dig=3
        )

    def test_send_negative_sum_from_account_erc20(self):
        """Send negative sum from account: ERC20"""

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20/ERC20.sol",
            "0.8.8",
            self.sender_account,
            contract_name="ERC20",
            constructor_args=["Test Token", "TT", DEFAULT_ERC20_BALANCE],
        )
        assert (
            contract.functions.balanceOf(self.sender_account.address).call()
            == DEFAULT_ERC20_BALANCE
        )
        initial_sender_neon_balance, initial_recipient_neon_balance = (
            self.sender_account_balance,
            self.recipient_account_balance,
        )

        with pytest.raises(web3.exceptions.ValidationError):
            self.web3_client.send_erc20(
                self.sender_account,
                self.recipient_account.address,
                -1,
                contract_deploy_tx["contractAddress"],
                abi=contract.abi,
            )

        # ERC20 balance
        assert (
            contract.functions.balanceOf(self.sender_account.address).call()
            == DEFAULT_ERC20_BALANCE
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        # Neon balance
        self.assert_balance(
            self.sender_account.address,
            initial_sender_neon_balance,
            rnd_dig=0,
        )
        self.assert_balance(
            self.recipient_account.address, initial_recipient_neon_balance, rnd_dig=3
        )

    def test_send_token_to_self_neon(self):
        """Send token to self: Neon"""
        transfer_amount = 2
        balance_before = self.sender_account_balance

        self.send_neon(self.sender_account, self.recipient_account, transfer_amount)
        self.assert_balance_less(
            self.sender_account.address,
            balance_before - transfer_amount,
        )

    def test_send_token_to_self_erc20(self):
        """Send token to self: ERC20"""

        transfer_amount = 10
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20/ERC20.sol",
            "0.8.8",
            self.sender_account,
            contract_name="ERC20",
            constructor_args=["Test Token", "TT", DEFAULT_ERC20_BALANCE],
        )
        assert (
            contract.functions.balanceOf(self.sender_account.address).call()
            == DEFAULT_ERC20_BALANCE
        )
        initial_sender_neon_balance = self.sender_account_balance

        self.web3_client.send_erc20(
            self.sender_account,
            self.sender_account.address,
            transfer_amount,
            contract_deploy_tx["contractAddress"],
            abi=contract.abi,
        )

        # ERC20 balance (now the balance is the same as before the transfer)
        assert (
            contract.functions.balanceOf(self.sender_account.address).call()
            == DEFAULT_ERC20_BALANCE
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        # Neon balance
        assert initial_sender_neon_balance > self.get_balance_from_wei(
            self.sender_account.address
        )

    @pytest.mark.parametrize("size", [4, 20])
    def test_send_token_to_an_invalid_address(self, size):
        """Send token to an invalid and not-existing address"""
        balance_before = self.sender_account_balance
        invalid_account = AccountData(address=gen_hash_of_block(size))
        self.send_neon_with_failure(
            sender_account=self.sender_account,
            recipient_account=invalid_account,
            amount=InputTestConstants.DEFAULT_TRANSFER_AMOUNT.value,
            exception=web3.exceptions.InvalidAddress,
        )

        balance_after = self.sender_account_balance
        assert balance_before == balance_after

    def test_check_erc_1820_transaction(self):
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
            "./NDEV1004/ContractOne.sol", "0.8.15", account=self.sender_account
        )
        address = contract_deploy_tx["contractAddress"]

        contractTwo, _ = self.web3_client.deploy_and_get_contract(
            "./NDEV1004/ContractTwo.sol", "0.8.15", account=self.sender_account
        )
        balance = contractTwo.functions.getBalance().call()
        assert balance == 0
        contractTwo.functions.depositOnContractOne(address).call()


@allure.story("Verify transactions validation")
class TestTransactionsValidation(BaseMixin):
    @pytest.mark.parametrize(
        "gas_limit,gas_price,expected_message", GAS_LIMIT_AND_PRICE_DATA
    )
    def test_generate_bad_sign(self, gas_limit, gas_price, expected_message):
        """Generate bad sign (when v, r, s over allowed size)
        Too low gas_limit
        Too high gas_limit > u64::max
        Too high gas_limit > u64::max
        Too high gas_price > u64::max
        Too high gas_limit * gas_price > u64::max
        """

        amount = 100
        sender_account = self.create_account_with_balance(amount)
        recipient_account = self.create_account_with_balance()

        self.send_neon_with_failure(
            sender_account=sender_account,
            recipient_account=recipient_account,
            amount=InputTestConstants.DEFAULT_TRANSFER_AMOUNT.value,
            gas=gas_limit,
            gas_price=gas_price,
            error_message=expected_message,
        )

        self.assert_balance(sender_account.address, amount)
        self.assert_balance(
            recipient_account.address,
            InputTestConstants.FAUCET_1ST_REQUEST_AMOUNT.value,
        )

    def test_send_the_same_transactions_if_accepted(self):
        """Transaction cannot be sent again if it was accepted"""
        transaction = self.create_tx_object()
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        params = [signed_tx.rawTransaction.hex()]
        response = self.proxy_api.send_rpc("eth_sendRawTransaction", params)
        self.wait_transaction_accepted(response["result"])
        response = self.proxy_api.send_rpc("eth_sendRawTransaction", params)
        assert ErrorMessage.ALREADY_KNOWN.value in response["error"]["message"]
        assert response["error"]["code"] == -32000

    def test_send_the_same_transactions_if_not_accepted(self):
        """Transaction can be sent again if it was not accepted"""
        transaction = self.create_tx_object()
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        params = [signed_tx.rawTransaction.hex()]
        self.proxy_api.send_rpc("eth_sendRawTransaction", params)
        response = self.proxy_api.send_rpc("eth_sendRawTransaction", params)
        assert "error" not in response
        assert "result" in response

    def test_send_transaction_with_small_gas_amount(self):
        """Check that transaction can't be sent if gas value is too small"""
        gas_price = random.randint(0, 10000)
        transaction = self.create_tx_object(gas_price=gas_price)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        pattern = (
            str.format(ErrorMessage.TRANSACTION_UNDERPRICED.value, gas_price) + r" \d.*"
        )
        assert re.match(pattern, response["error"]["message"])
        assert response["error"]["code"] == -32000

    def test_send_transaction_with_old_nonce(self):
        """Check that transaction with old nonce can't be sent"""
        nonce = self.web3_client.eth.get_transaction_count(self.sender_account.address)
        transaction = self.create_tx_object(amount=1, nonce=nonce)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        self.wait_transaction_accepted(response["result"])

        transaction = self.create_tx_object(amount=2, nonce=nonce)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        assert ErrorMessage.NONCE_TOO_LOW.value in response["error"]["message"]
        assert response["error"]["code"] == -32002

    def test_send_too_big_transaction(self):
        """Transaction size is too big"""
        transaction = self.create_tx_object()
        transaction["data"] = gen_hash_of_block(256 * 1024)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        params = [signed_tx.rawTransaction.hex()]
        response = self.proxy_api.send_rpc("eth_sendRawTransaction", params)
        assert ErrorMessage.TOO_BIG_TRANSACTION.value in response["error"]["message"]
        assert response["error"]["code"] == -32000

    @pytest.mark.skip(reason="We should rewrite this test, because it need new account")
    def test_send_transaction_with_small_gas_price(self):
        """Check that transaction can't be sent if gas value is too small"""
        gas_price = self.web3_client.gas_price()
        transaction = self.create_tx_object(gas_price=(int(gas_price * 0.92)))
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        receipt = self.wait_transaction_accepted(response["result"])

    @pytest.mark.xfail(reason="NDEV-628")
    def test_big_memory_value(self):
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "BigMemoryValue", "0.8.12", account=self.sender_account
        )
        bytes_amount = contract.functions.makeBigMemoryValue(13).call()
        assert bytes_amount > 16 * 1024 * 1024

    @pytest.mark.parametrize(
        "amount",
        [eth_utils.denoms.gwei, eth_utils.denoms.gwei + eth_utils.denoms.gwei * 0.5],
    )
    def test_transfer_gweis(self, amount):
        sender = self.create_account_with_balance(1)
        recipient = self.create_account()
        sender_balance_before = self.web3_client.eth.get_balance(sender.address)
        recipient_balance_before = self.web3_client.eth.get_balance(recipient.address)

        transaction = self.create_tx_object(
            sender=sender.address,
            recipient=recipient.address,
            amount=web3.Web3.fromWei(amount, "ether"),
        )
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, sender.key
        )

        params = [signed_tx.rawTransaction.hex()]
        transaction = self.proxy_api.send_rpc("eth_sendRawTransaction", params)[
            "result"
        ]

        self.wait_transaction_accepted(transaction)
        sender_balance_after = self.web3_client.eth.get_balance(sender.address)
        recipient_balance_after = self.web3_client.eth.get_balance(recipient.address)

        assert sender_balance_after < sender_balance_before - amount
        assert recipient_balance_after == recipient_balance_before + amount
