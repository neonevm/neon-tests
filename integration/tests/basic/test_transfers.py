import allure
from marshmallow import ValidationError
import pytest
from typing import Union

import web3
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import WAITING_FOR_MS, BaseMixin
from integration.tests.basic.helpers.error_message import ErrorMessage
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.model.model import AccountData
from integration.tests.basic.test_data.input_data import InputData


INVALID_ADDRESS = AccountData(address="0x12345")
ENS_NAME_ERROR = f"ENS name: '{INVALID_ADDRESS.address}' is invalid."
EIP55_INVALID_CHECKSUM = (
    "'Address has an invalid EIP-55 checksum. After looking up the address from the original source, try again.'"
)
U64_MAX = 18_446_744_073_709_551_615


WRONG_TRANSFER_AMOUNT_DATA = [(11000_501), (10000_000.1)]
TRANSFER_AMOUNT_DATA = [(0.01), (1), (1.1)]

GAS_LIMIT_AND_PRICE_DATA = (
    [1, None, ErrorMessage.GAS_LIMIT_REACHED.value],
    [U64_MAX + 1, None, ErrorMessage.INSUFFICIENT_FUNDS.value],
    [
        0,
        U64_MAX + 1,
        ErrorMessage.INSUFFICIENT_FUNDS.value,
    ],
    [1, (U64_MAX + 1), ErrorMessage.GAS_LIMIT_REACHED.value],
    [1000, int((U64_MAX + 100) / 1000), ErrorMessage.GAS_LIMIT_REACHED.value],
)


@allure.story("Basic: transfer tests")
class TestTransfer(BaseMixin):
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_neon_from_one_account_to_another(self, amount: Union[int, float]):
        """Send neon from one account to another"""
        sender_balance = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))

        tx_receipt = self.process_transaction(self.sender_account, self.recipient_account, amount)
        self.assert_balance(
            self.sender_account.address,
            sender_balance - amount - self.calculate_trx_gas(tx_receipt=tx_receipt),
            rnd_dig=1,
        )
        self.assert_balance(self.recipient_account.address, recipient_balance + amount, rnd_dig=3)

    def test_send_erc20_token_from_one_account_to_another(self, erc20wrapper):
        """Send erc20 token from one account to another"""
        transfer_amount = 5

        contract, spl_owner = erc20wrapper
        initial_balance = contract.functions.balanceOf(self.recipient_account.address).call()

        transfer_tx = self.web3_client.send_erc20(
            spl_owner, self.recipient_account, transfer_amount, contract.address, abi=contract.abi
        )

        assert contract.functions.balanceOf(self.recipient_account.address).call() == initial_balance + transfer_amount

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_send_spl_wrapped_account_from_one_account_to_another(self):  # , erc20wrapper):
        """Send spl wrapped account from one account to another"""
        assert 1 == 2

    @pytest.mark.parametrize("amount", WRONG_TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_neon(self, amount: Union[int, float]):
        """Send more than exist on account: neon"""

        sender_balance = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))
        self.check_value_error_if_less_than_required(self.sender_account, self.recipient_account, amount)

        self.assert_balance(self.sender_account.address, sender_balance, rnd_dig=1)
        self.assert_balance(self.recipient_account.address, recipient_balance, rnd_dig=1)

    @pytest.mark.skip(WAITING_FOR_MS)
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_spl(self, amount):
        """Send more than exist on account: spl (with different precision)"""
        assert 1 == 2

    def test_send_more_than_exist_on_account_erc20(self, erc20wrapper):
        """Send more than exist on account: ERC20"""
        transfer_amount = 1_000_000_000_000_000_000_000

        contract, spl_owner = erc20wrapper
        initial_amount = contract.functions.balanceOf(self.recipient_account.address).call()

        with pytest.raises(web3.exceptions.ContractLogicError) as error_info:
            transfer_tx = self.web3_client.send_erc20(
                spl_owner, self.recipient_account, transfer_amount, contract.address, abi=contract.abi
            )

        assert error_info, AssertMessage.TRX_NOT_FAILED.value

        assert contract.functions.balanceOf(self.recipient_account.address).call() == initial_amount

    def test_zero_neon(self):
        """Send zero: neon"""

        sender_balance = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))
        tx_receipt = self.process_transaction(self.sender_account, self.recipient_account)

        self.assert_balance(
            self.sender_account.address, sender_balance - self.calculate_trx_gas(tx_receipt=tx_receipt), rnd_dig=1
        )
        self.assert_balance(self.recipient_account.address, recipient_balance, rnd_dig=1)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_zero_spl(self):
        """Send zero: spl (with different precision)"""
        assert 1 == 2

    def test_zero_erc20(self, erc20wrapper):
        """Send zero: ERC20"""
        transfer_amount = 0

        contract, spl_owner = erc20wrapper
        initial_balance = contract.functions.balanceOf(self.recipient_account.address).call()

        transfer_tx = self.web3_client.send_erc20(
            spl_owner, self.recipient_account, transfer_amount, contract.address, abi=contract.abi
        )

        assert contract.functions.balanceOf(self.recipient_account.address).call() == initial_balance

    def test_send_negative_sum_from_account_neon(self):
        """Send negative sum from account: neon"""

        sender_balance = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        recipient_balance = float(self.web3_client.fromWei(self.get_balance(self.recipient_account.address), "ether"))
        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            InputData.NEGATIVE_AMOUNT.value,
            ErrorMessage.NEGATIVE_VALUE.value,
        )

        self.assert_balance(self.sender_account.address, sender_balance, rnd_dig=1)
        self.assert_balance(self.recipient_account.address, recipient_balance, rnd_dig=1)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_send_negative_sum_from_account_spl(self):
        """Send negative sum from account: spl (with different precision)"""
        assert 1 == 2

    def test_send_negative_sum_from_account_erc20(self, erc20wrapper):
        """Send negative sum from account: ERC20"""
        transfer_amount = -1

        contract, spl_owner = erc20wrapper
        initial_balance = contract.functions.balanceOf(self.recipient_account.address).call()

        with pytest.raises(web3.exceptions.ValidationError) as error_info:
            transfer_tx = self.web3_client.send_erc20(
                spl_owner, self.recipient_account, transfer_amount, contract.address, abi=contract.abi
            )

        assert error_info, AssertMessage.TRX_NOT_FAILED.value

        assert contract.functions.balanceOf(self.recipient_account.address).call() == initial_balance

    def test_send_token_to_an_invalid_address(self):
        """Send token to an invalid address"""
        sender_account = self.create_account_with_balance()
        balance_before = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))
        self.process_transaction_with_failure(
            sender_account,
            INVALID_ADDRESS,
            InputData.DEFAULT_TRANSFER_AMOUNT.value,
            ENS_NAME_ERROR,
        )
        balance_after = float(self.web3_client.fromWei(self.get_balance(self.sender_account.address), "ether"))

        assert balance_before == balance_after

    def test_send_more_token_to_non_existing_address(self):
        """Send token to a non-existing address"""
        sender_account = self.create_account_with_balance()
        recipient_address = AccountData(address=sender_account.address.replace("1", "2").replace("3", "4"))

        self.process_transaction_with_failure(
            sender_account,
            recipient_address,
            InputData.DEFAULT_TRANSFER_AMOUNT.value,
            error_message=EIP55_INVALID_CHECKSUM,
        )

        self.assert_balance(sender_account.address, InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    def test_check_erc_1820_transaction(self):
        """Check ERC-1820 transaction (without chain_id in sign)"""

        amount = 100
        sender_account = self.create_account_with_balance(amount)
        recipient_account = self.create_account_with_balance()
        transfer_amount = 2

        transaction = {
            "from": sender_account.address,
            "to": recipient_account.address,
            "value": self.web3_client.toWei(transfer_amount, "ether"),
            "gasPrice": self.web3_client.gas_price(),
            "gas": 0,
            "nonce": self.web3_client.eth.get_transaction_count(sender_account.address),
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)

        params = [signed_tx.rawTransaction.hex()]
        model = RpcRequestFactory.build_send_raw_trx(params=params)
        actual_result = self.json_rpc_client.do_call(model)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(actual_result), AssertMessage.WRONG_TYPE.value
        assert "0x" in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

        self.assert_balance(sender_account.address, amount - transfer_amount)
        self.assert_balance(recipient_account.address, InputData.FAUCET_1ST_REQUEST_AMOUNT.value + transfer_amount)


@allure.story("Basic: transactions validation")
class TestTransactionsValidation(BaseMixin):
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

        self.process_transaction_with_failure(
            sender_account,
            recipient_account,
            amount=InputData.DEFAULT_TRANSFER_AMOUNT.value,
            gas=gas_limit,
            gas_price=gas_price,
            error_message=expected_message,
        )

        self.assert_balance(sender_account.address, amount)
        self.assert_balance(recipient_account.address, InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    def test_send_with_big_nonce(self):
        """Nonce is too high"""
        amount = 2

        transaction = self.create_tx_object(amount, 1_000_000_000)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]
        model = RpcRequestFactory.build_send_raw_trx(params=params)
        actual_result = self.json_rpc_client.do_call(model)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert (
            ErrorMessage.NONCE_TOO_HIGH.value in actual_result.error["message"]
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
        model = RpcRequestFactory.build_send_raw_trx(params=params)
        actual_result = self.json_rpc_client.do_call(model)

        # 2nd transaction (with low nonce)
        transaction = self.create_tx_object(amount, 0)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]
        model = RpcRequestFactory.build_send_raw_trx(params=params)
        actual_result = self.json_rpc_client.do_call(model)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert (
            ErrorMessage.NONCE_TOO_LOW.value in actual_result.error["message"]
        ), AssertMessage.DOES_NOT_CONTAIN_TOO_LOW.value

    def test_there_are_not_enough_neons_for_gas_fee(self):
        """There are not enough Neons for gas fee"""
        sender_amount = 1
        sender_account = self.create_account_with_balance(sender_amount)
        recipient_account = self.web3_client.create_account()
        amount = 0.9

        balance_before = float(self.web3_client.fromWei(self.get_balance(sender_account.address), "ether"))
        self.process_transaction_with_failure(
            sender_account,
            recipient_account,
            amount,
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

        self.process_transaction_with_failure(
            sender_account,
            recipient_account,
            amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value,
        )

        self.assert_balance(sender_account.address, sender_amount)
        self.assert_balance(recipient_account.address, 0)

    def create_tx_object(self, amount, nonce):
        transaction = {
            "from": self.sender_account.address,
            "to": self.recipient_account.address,
            "value": self.web3_client.toWei(amount, "ether"),
            "chainId": self.web3_client._chain_id,
            "gasPrice": self.web3_client.gas_price(),
            "gas": 0,
            "nonce": nonce,
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        return transaction
