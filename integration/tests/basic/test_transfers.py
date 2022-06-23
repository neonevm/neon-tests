import typing as tp

import allure
import pytest
import web3

from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.assert_message import ErrorMessage
from utils.consts import Unit, InputTestConstants

U64_MAX = 18_446_744_073_709_551_615
DEFAULT_ERC20_BALANCE = 1000


GAS_LIMIT_AND_PRICE_DATA = (
    [1, None, ErrorMessage.GAS_LIMIT_REACHED.value],
    [U64_MAX + 1, None, ErrorMessage.INSUFFICIENT_FUNDS.value],
    [
        0,
        U64_MAX + 1,
        ErrorMessage.INSUFFICIENT_FUNDS.value,
    ],
    [1, (U64_MAX + 1), ErrorMessage.GAS_LIMIT_REACHED.value],
    [1_000, int((U64_MAX + 100) / 1_000), ErrorMessage.GAS_LIMIT_REACHED.value],
)


@allure.story("Basic: transfer tests")
class TestTransfer(BaseMixin):
    @pytest.mark.parametrize("transfer_amount", [0, 0.1, 1, 1.1])
    def test_send_neon_from_one_account_to_another(self, transfer_amount: tp.Union[int, float]):
        """Send neon from one account to another"""
        initial_sender_balance, initial_recipient_balance = self.sender_account_balance, self.recipient_account_balance
        self.send_neon(self.sender_account, self.recipient_account, transfer_amount)
        self.assert_balance_less(self.sender_account.address, initial_sender_balance - transfer_amount)
        self.assert_balance(self.recipient_account.address, initial_recipient_balance + transfer_amount, rnd_dig=3)

    @pytest.mark.parametrize("transfer_amount", [0, 1, 10, 100])
    def test_send_erc20_token_from_one_account_to_another(self, transfer_amount: tp.Union[int, float]):
        """Send erc20 token from one account to another"""

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20", "0.6.6", self.sender_account, constructor_args=[DEFAULT_ERC20_BALANCE]
        )
        assert contract.functions.balanceOf(self.sender_account.address).call() == DEFAULT_ERC20_BALANCE
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

        # ERC20 balance
        assert (
            contract.functions.balanceOf(self.sender_account.address).call() == DEFAULT_ERC20_BALANCE - transfer_amount
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        self.assert_balance_less(
            self.sender_account.address, initial_sender_neon_balance - self.calculate_trx_gas(tx_receipt=tx_receipt)
        )
        self.assert_balance(self.recipient_account.address, initial_recipient_neon_balance, rnd_dig=3)

    @pytest.mark.parametrize("transfer_amount", [0, 1, 10, 100])
    def test_send_spl_wrapped_account_from_one_account_to_another(self, transfer_amount: int, erc20wrapper):
        """Send spl wrapped account from one account to another"""

        contract, spl_owner = erc20wrapper
        initial_spl_balance = contract.functions.balanceOf(self.recipient_account.address).call()
        initial_neon_balance = self.recipient_account_balance

        self.web3_client.send_erc20(
            spl_owner, self.recipient_account, transfer_amount, contract.address, abi=contract.abi
        )

        # Spl balance
        assert (
            contract.functions.balanceOf(self.recipient_account.address).call() == initial_spl_balance + transfer_amount
        )

        # Neon balance
        self.assert_balance(self.recipient_account.address, initial_neon_balance, rnd_dig=3)

    @pytest.mark.parametrize("amount", [11_000_501, 10_000_000.1])
    def test_send_more_than_exist_on_account_neon(self, amount: tp.Union[int, float]):
        """Send more than exist on account: neon"""

        sender_balance, recipient_balance = self.sender_account_balance, self.recipient_account_balance
        self.check_value_error_if_less_than_required(self.sender_account, self.recipient_account, amount)

        self.assert_balance(self.sender_account.address, sender_balance, rnd_dig=1)
        self.assert_balance(self.recipient_account.address, recipient_balance, rnd_dig=1)

    def test_send_more_than_exist_on_account_spl(self, erc20wrapper):
        """Send more than exist on account: spl (with different precision)"""

        transfer_amount = 1_000_000_000_000_000_000_000
        contract, spl_owner = erc20wrapper
        initial_spl_balance = contract.functions.balanceOf(self.recipient_account.address).call()
        initial_neon_balance = self.recipient_account_balance

        with pytest.raises(web3.exceptions.ContractLogicError):
            self.web3_client.send_erc20(
                spl_owner, self.recipient_account, transfer_amount, contract.address, abi=contract.abi
            )

        # Spl balance
        assert contract.functions.balanceOf(self.recipient_account.address).call() == initial_spl_balance

        # Neon balance
        self.assert_balance(self.recipient_account.address, initial_neon_balance, rnd_dig=3)

    def test_send_more_than_exist_on_account_erc20(self):
        """Send more than exist on account: ERC20"""

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20", "0.6.6", self.sender_account, constructor_args=[DEFAULT_ERC20_BALANCE]
        )
        assert contract.functions.balanceOf(self.sender_account.address).call() == DEFAULT_ERC20_BALANCE
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
            contract.functions.balanceOf(self.sender_account.address).call() == DEFAULT_ERC20_BALANCE
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        # Neon balance
        self.assert_balance(
            self.sender_account.address,
            initial_sender_neon_balance,
            rnd_dig=0,
        )
        self.assert_balance(self.recipient_account.address, initial_recipient_neon_balance, rnd_dig=3)

    def test_send_negative_sum_from_account_neon(self):
        """Send negative sum from account: neon"""

        sender_balance, recipient_balance = self.sender_account_balance, self.recipient_account_balance

        self.send_neon_with_failure(
            sender_account=self.sender_account,
            recipient_account=self.recipient_account,
            amount=InputTestConstants.NEGATIVE_AMOUNT.value,
            error_message=ErrorMessage.NEGATIVE_VALUE.value,
        )

        self.assert_balance(self.sender_account.address, sender_balance, rnd_dig=0)
        self.assert_balance(self.recipient_account.address, recipient_balance, rnd_dig=1)

    def test_send_negative_sum_from_account_spl(self, erc20wrapper):
        """Send negative sum from account: spl (with different precision)"""

        transfer_amount = -1
        contract, spl_owner = erc20wrapper
        initial_spl_balance = contract.functions.balanceOf(self.recipient_account.address).call()
        initial_neon_balance = self.recipient_account_balance

        with pytest.raises(web3.exceptions.ValidationError):
            self.web3_client.send_erc20(
                spl_owner, self.recipient_account, transfer_amount, contract.address, abi=contract.abi
            )

        # Spl balance
        assert contract.functions.balanceOf(self.recipient_account.address).call() == initial_spl_balance

        # Neon balance
        self.assert_balance(self.recipient_account.address, initial_neon_balance, rnd_dig=3)

    def test_send_negative_sum_from_account_erc20(self):
        """Send negative sum from account: ERC20"""

        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "ERC20", "0.6.6", self.sender_account, constructor_args=[DEFAULT_ERC20_BALANCE]
        )
        assert contract.functions.balanceOf(self.sender_account.address).call() == DEFAULT_ERC20_BALANCE
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
            contract.functions.balanceOf(self.sender_account.address).call() == DEFAULT_ERC20_BALANCE
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value

        # Neon balance
        self.assert_balance(
            self.sender_account.address,
            initial_sender_neon_balance,
            rnd_dig=0,
        )
        self.assert_balance(self.recipient_account.address, initial_recipient_neon_balance, rnd_dig=3)

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
            "ERC20", "0.6.6", self.sender_account, constructor_args=[DEFAULT_ERC20_BALANCE]
        )
        assert contract.functions.balanceOf(self.sender_account.address).call() == DEFAULT_ERC20_BALANCE
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
            contract.functions.balanceOf(self.sender_account.address).call() == DEFAULT_ERC20_BALANCE
        ), AssertMessage.CONTRACT_BALANCE_IS_WRONG.value
        # Neon balance
        self.assert_balance(self.sender_account.address, initial_sender_neon_balance, rnd_dig=0)

    def test_send_token_to_an_invalid_address(self):
        """Send token to an invalid address"""
        balance_before = self.sender_account_balance

        self.send_neon_with_failure(
            sender_account=self.sender_account,
            recipient_account=self.invalid_account,
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

        transaction = {
            "from": sender_account.address,
            "to": recipient_account.address,
            "value": self.web3_client.toWei(transfer_amount, Unit.ETHER),
            "gasPrice": self.web3_client.gas_price(),
            "gas": 0,
            "nonce": self.web3_client.eth.get_transaction_count(sender_account.address),
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)

        params = [signed_tx.rawTransaction.hex()]
        actual_result = self.json_rpc_client.send_rpc("eth_sendRawTransaction", params)

        assert "0x" in actual_result["result"], AssertMessage.DOES_NOT_START_WITH_0X.value

        self.assert_balance(sender_account.address, amount - transfer_amount)
        self.assert_balance(recipient_account.address, InputTestConstants.FAUCET_1ST_REQUEST_AMOUNT.value + transfer_amount)


@allure.story("Basic: transactions validation")
class TestTransactionsValidation(BaseMixin):
    def create_tx_object(self, amount, nonce):
        transaction = {
            "from": self.sender_account.address,
            "to": self.recipient_account.address,
            "value": self.web3_client.toWei(amount, Unit.ETHER),
            "chainId": self.web3_client._chain_id,
            "gasPrice": self.web3_client.gas_price(),
            "gas": 0,
            "nonce": nonce,
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        return transaction

    @pytest.mark.parametrize("gas_limit,gas_price,expected_message", GAS_LIMIT_AND_PRICE_DATA)
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
        self.assert_balance(recipient_account.address, InputTestConstants.FAUCET_1ST_REQUEST_AMOUNT.value)

    def test_send_with_big_nonce(self):
        """Nonce is too high"""
        amount = 2

        transaction = self.create_tx_object(amount, 1_000_000_000)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]
        actual_result = self.json_rpc_client.send_rpc("eth_sendRawTransaction", params)

        assert (
            ErrorMessage.NONCE_TOO_HIGH.value in actual_result["error"]["message"]
        ), AssertMessage.DOES_NOT_CONTAIN_TOO_HIGH.value

    def test_send_with_old_nonce(self):
        """Nonce is too low"""

        amount = 2

        # 1st transaction
        transaction = self.create_tx_object(
            amount, self.web3_client.eth.get_transaction_count(self.sender_account.address)
        )
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]
        self.json_rpc_client.send_rpc("eth_sendRawTransaction", params)

        # 2nd transaction (with low nonce)
        transaction = self.create_tx_object(amount, 0)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]
        actual_result = self.json_rpc_client.send_rpc("eth_sendRawTransaction", params)

        assert (
            ErrorMessage.NONCE_TOO_LOW.value in actual_result["error"]["message"]
        ), AssertMessage.DOES_NOT_CONTAIN_TOO_LOW.value

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
