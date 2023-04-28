import time
import typing as tp
from dataclasses import dataclass
from decimal import Decimal

import allure
import pytest
import web3
import eth_account.signers.local
from solana.publickey import PublicKey
from solana.rpc.commitment import Finalized
from solders.rpc.errors import InternalErrorMessage
from solders.rpc.responses import GetTransactionResp
from solders.signature import Signature

from utils.consts import Unit, InputTestConstants
from utils.helpers import gen_hash_of_block, wait_condition
from utils.apiclient import JsonRPCSession
from integration.tests.base import BaseTests


@dataclass
class AccountData:
    address: str
    key: str = ""


class BaseMixin(BaseTests):
    proxy_api: JsonRPCSession = None
    _sender_account: eth_account.signers.local.LocalAccount = None
    _recipient_account: eth_account.signers.local.LocalAccount = None
    _invalid_account: AccountData = None
    evm_loader_id = None

    @pytest.fixture(autouse=True)
    def prepare_env(self, json_rpc_client):
        self.proxy_api = json_rpc_client

    @property
    def sender_account(self):
        if not self._sender_account:
            account = self.create_account_with_balance()
            self._sender_account = account
        return self._sender_account

    @property
    def recipient_account(self):
        if not self._recipient_account:
            account = self.create_account_with_balance()
            self._recipient_account = account
        return self._recipient_account

    @property
    def invalid_account(self):
        if not self._recipient_account:
            account = self.create_invalid_account()
            self._invalid_account = account
        return self._invalid_account

    @property
    def sender_account_balance(self):
        return self.get_balance_from_wei(self.sender_account.address)

    @property
    def recipient_account_balance(self):
        return self.get_balance_from_wei(self.recipient_account.address)

    @pytest.fixture(autouse=True)
    def prepare_account(self):
        """Prevents calling to a fixture with the same name from operators' tests"""
        pass

    def create_account(self):
        """Creates a new account"""
        return self.web3_client.create_account()

    def get_balance_from_wei(self, address: str) -> float:
        """Gets balance from Wei"""
        return float(self.web3_client.from_wei(self.web3_client.eth.get_balance(address), Unit.ETHER))

    def create_account_with_balance(
            self, amount: int = InputTestConstants.FAUCET_1ST_REQUEST_AMOUNT.value
    ):
        """Creates a new account with balance"""
        account = self.create_account()
        balance_before = self.get_balance_from_wei(account.address)
        self.faucet.request_neon(account.address, amount=amount)
        for _ in range(20):
            if self.get_balance_from_wei(account.address) >= (balance_before + amount):
                break
            time.sleep(1)
        else:
            raise AssertionError(f"Balance didn't changed after 20 seconds ({account.address})")
        return account

    @staticmethod
    def create_invalid_account() -> AccountData:
        """Create non existing account"""
        return AccountData(address=gen_hash_of_block(20))

    def send_neon(
            self,
            sender_account: eth_account.signers.local.LocalAccount,
            recipient_account: eth_account.signers.local.LocalAccount,
            amount: float = 0.0,
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Processes transaction"""
        with allure.step(f"Sending {amount} from {sender_account.address} to {recipient_account.address}"):
            return self.web3_client.send_neon(sender_account, recipient_account, amount)

    def send_neon_with_failure(
            self,
            sender_account: eth_account.signers.local.LocalAccount,
            recipient_account: tp.Union[eth_account.signers.local.LocalAccount, AccountData],
            amount: tp.Union[int, float, Decimal],
            gas: tp.Optional[int] = 0,
            gas_price: tp.Optional[int] = None,
            error_message: str = None,
            exception: tp.Any = None,
    ) -> tp.Union[web3.types.TxReceipt, None]:
        """Processes transaction, expects a failure"""
        exception = exception or Exception
        with allure.step(f"Sending {amount} from {sender_account.address} to {recipient_account.address}"):
            with pytest.raises(exception, match=error_message):
                return self.web3_client.send_neon(sender_account, recipient_account, amount, gas, gas_price)

    def assert_balance(self, address: str, expected_amount: float, rnd_dig: int = None):
        """Compares balance of an account with expectation"""
        balance = self.get_balance_from_wei(address)
        self.check_balance(expected_amount, balance, rnd_dig=rnd_dig)

    def assert_balance_less(
            self,
            address: str,
            calculated_balance: float,
    ):
        """Compares balance of an account, balance must be less than init balance"""
        balance = self.get_balance_from_wei(address)
        assert round(balance) <= round(
            calculated_balance
        ), f"Balance after transferring {balance} must be less or equal {calculated_balance}"

    @allure.step("calculating gas")
    def calculate_trx_gas(self, tx_receipt: web3.types.TxReceipt) -> float:
        gas_used_in_tx = tx_receipt.cumulativeGasUsed * self.web3_client.from_wei(
            self.web3_client.gas_price(), Unit.ETHER
        )
        return float(round(gas_used_in_tx, InputTestConstants.ROUND_DIGITS.value))

    @allure.step("calculating gas")
    def calculate_trx_gas(self, tx_receipt: web3.types.TxReceipt) -> float:
        gas_used_in_tx = tx_receipt.cumulativeGasUsed * self.web3_client.from_wei(
            self.web3_client.gas_price(), Unit.ETHER
        )
        return float(round(gas_used_in_tx, InputTestConstants.ROUND_DIGITS.value))

    @staticmethod
    def assert_no_error_object(data) -> bool:
        """Checks that the error sub object is not present"""
        return not hasattr(data, "error")

    @staticmethod
    def check_balance(expected: float, actual: float, rnd_dig: int = InputTestConstants.ROUND_DIGITS.value):
        """Compares the balance with expectation"""
        expected_dec = round(expected, rnd_dig)
        actual_dec = round(actual, rnd_dig)

        assert actual_dec == expected_dec, f"expected balance = {expected_dec}, actual balance = {actual_dec}"

    def wait_transaction_accepted(self, transaction, timeout=20):
        started = time.time()
        while (time.time() - started) < timeout:
            receipt = self.proxy_api.send_rpc(method="eth_getTransactionReceipt", params=[transaction])
            if receipt['result'] is not None:
                return receipt
            time.sleep(1)
        raise TimeoutError(f"Transaction is not accepted for {timeout} seconds")

    def create_tx_object(self, sender=None, recipient=None, amount=2, nonce=None, gas_price=None, data=None):
        if gas_price is None:
            gas_price = self.web3_client.gas_price()
        if sender is None:
            sender = self.sender_account.address
        if recipient is None:
            recipient = self.recipient_account.address
        if nonce is None:
            nonce = self.web3_client.eth.get_transaction_count(sender)
        transaction = {
            "from": sender,
            "to": recipient,
            "value": self.web3_client.to_wei(amount, Unit.ETHER),
            "chainId": self.web3_client._chain_id,
            "gasPrice": gas_price,
            "gas": 0,
            "nonce": nonce,
        }
        if data is not None:
            transaction["data"] = data
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)
        return transaction

    def create_contract_call_tx_object(self, sender=None, amount=None):
        if sender is None:
            sender = self.sender_account
        tx = {
            "from": sender.address,
            "nonce": self.web3_client.eth.get_transaction_count(
                sender.address
            ),
            "gasPrice": self.web3_client.gas_price(),
        }
        if amount is not None:
            tx["value"] = self.web3_client.to_wei(amount, Unit.ETHER)
        return tx



    def get_solana_resps_by_neon_resp(self, resp):
        solana_resps = []
        solana_trx = self.web3_client.get_solana_trx_by_neon(resp["transactionHash"].hex())
        for trx in solana_trx['result']:
            wait_condition(
                lambda: self.sol_client.get_transaction(Signature.from_string(trx),
                                                        max_supported_transaction_version=0) != GetTransactionResp(
                    None))
            trx_sol = self.sol_client.get_transaction(Signature.from_string(trx), max_supported_transaction_version=0)
            solana_resps.append(trx_sol)
        return solana_resps
