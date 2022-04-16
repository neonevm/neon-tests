import allure
import pytest
from typing import Union
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.basic import WAITING_FOR_ERC20, WAITING_FOR_MS, BasicTests
from integration.tests.basic.helpers.error_message import ErrorMessage
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.model.model import AccountData,  TrxReceiptResponse, TrxResponse
from integration.tests.basic.model.tags import Tag
from integration.tests.basic.test_data.input_data import InputData

INVALID_ADDRESS = AccountData(address="0x12345")
ENS_NAME_ERROR = f"ENS name: '{INVALID_ADDRESS.address}' is invalid."
EIP55_INVALID_CHECKSUM = "'Address has an invalid EIP-55 checksum. After looking up the address from the original source, try again.'"
U64_MAX = 18_446_744_073_709_551_615

WRONG_TRANSFER_AMOUNT_DATA = [(1_501), (10_000.1)]
TRANSFER_AMOUNT_DATA = [(0.01), (1), (1.1)]

GAS_LIMIT_AND_PRICE_DATA = ([1, None, ErrorMessage.GAS_LIMIT_REACHED.value], [U64_MAX+1, None, ErrorMessage.INSUFFICIENT_FUNDS.value], [0, U64_MAX+1,
                            ErrorMessage.INSUFFICIENT_FUNDS.value], [1, (U64_MAX+1), ErrorMessage.INSUFFICIENT_FUNDS.value], [1000, int((U64_MAX+100)/1000), ErrorMessage.INSUFFICIENT_FUNDS.value])


@allure.story("Basic: transfer tests")
class TestTransfer(BasicTests):
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_neon_from_one_account_to_another(self, amount: Union[int,
                                                                       float],
                                                   prepare_accounts):
        """Send neon from one account to another"""

        tx_receipt = self.process_transaction(self.sender_account,
                                              self.recipient_account, amount)

        self.assert_balance(
            self.sender_account.address,
            InputData.FAUCET_1ST_REQUEST_AMOUNT.value - amount -
            self.calculate_trx_gas(tx_receipt=tx_receipt))
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value + amount)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_send_spl_wrapped_account_from_one_account_to_another(self):
        """Send spl wrapped account from one account to another"""
        pass

    @pytest.mark.parametrize("amount", WRONG_TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_neon(self, amount: Union[int,
                                                                      float],
                                                  prepare_accounts):
        """Send more than exist on account: neon"""

        self.check_value_error_if_less_than_required(self.sender_account,
                                                     self.recipient_account,
                                                     amount)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    @pytest.mark.skip(WAITING_FOR_MS)
    @pytest.mark.parametrize("amount", TRANSFER_AMOUNT_DATA)
    def test_send_more_than_exist_on_account_spl(self, amount):
        """Send more than exist on account: spl (with different precision)"""
        pass

    @pytest.mark.skip(WAITING_FOR_ERC20)
    def test_send_more_than_exist_on_account_erc20(self):
        """Send more than exist on account: ERC20"""
        pass

    def test_zero_neon(self, prepare_accounts):
        """Send zero: neon"""

        tx_receipt = self.process_transaction(self.sender_account,
                                              self.recipient_account)

        self.assert_balance(
            self.sender_account.address,
            InputData.FAUCET_1ST_REQUEST_AMOUNT.value -
            self.calculate_trx_gas(tx_receipt=tx_receipt))
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_zero_spl(self):
        """Send zero: spl (with different precision)"""
        pass

    @pytest.mark.xfail()
    def test_zero_erc20(self):
        """Send zero: ERC20"""
        pass

    def test_send_negative_sum_from_account_neon(self, prepare_accounts):
        """Send negative sum from account: neon"""

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            InputData.NEGATIVE_AMOUNT.value,
            error_message=ErrorMessage.NEGATIVE_VALUE.value)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    @pytest.mark.skip(WAITING_FOR_MS)
    def test_send_negative_sum_from_account_spl(self):
        """Send negative sum from account: spl (with different precision)"""
        pass

    @pytest.mark.skip(WAITING_FOR_ERC20)
    def test_send_negative_sum_from_account_erc20(self):
        """Send negative sum from account: ERC20"""
        pass

    def test_send_token_to_an_invalid_address(self):
        """Send token to an invalid address"""
        sender_account = self.create_account_with_balance()

        self.process_transaction_with_failure(
            sender_account,
            INVALID_ADDRESS,
            InputData.DEFAULT_TRANSFER_AMOUNT.value,
            error_message=ENS_NAME_ERROR)

        self.assert_balance(sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    def test_send_more_token_to_non_existing_address(self):
        """Send token to a non-existing address"""
        sender_account = self.create_account_with_balance()
        recipient_address = AccountData(
            address=sender_account.address.replace('1', '2').replace('3', '4'))

        self.process_transaction_with_failure(
            sender_account,
            recipient_address,
            InputData.DEFAULT_TRANSFER_AMOUNT.value,
            error_message=EIP55_INVALID_CHECKSUM)

        self.assert_balance(sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)

    """
    20.	Check ERC-1820 transaction (without chain_id in sign)		
    21.	Generate bad sign (when v, r, s over allowed size)		
        There are many known variants of, it's not possible to describe all of them.		
        Below are the simplest:		
    22.	Too low gas_limit		
    23.	Too high gas_limit > u64::max		
    24.	Too high gas_price > u64::max		
    25.	Too high gas_limit * gas_price > u64::max		
    26.	There are not enough Neons for gas fee		
    27.	There are not enough Neons for transfer
    """

    def test_there_are_not_enough_neons_for_gas_fee(self):
        """There are not enough Neons for gas fee"""
        sender_amount = 1
        self.sender_account = self.create_account_with_balance(sender_amount)
        self.recipient_account = self.web3_client.create_account()
        amount = 0.9

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value)

        self.assert_balance(self.sender_account.address, sender_amount)
        self.assert_balance(self.recipient_account.address, 0)

    def test_there_are_not_enough_neons_for_transfer(self):
        """There are not enough Neons for transfer"""
        sender_amount = 1
        self.sender_account = self.create_account_with_balance(sender_amount)
        self.recipient_account = self.web3_client.create_account()
        amount = 1.1

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            error_message=ErrorMessage.INSUFFICIENT_FUNDS.value)

        self.assert_balance(self.sender_account.address, sender_amount)
        self.assert_balance(self.recipient_account.address, 0)


'''
12.	Verify implemented rpc calls work
12.1.	eth_getBlockByHash		
12.2.	eth_getBlockByNumber		
12.11.	eth_blockNumber		
12.12.	eth_call		
12.13.	eth_estimateGas		
12.14.	eth_gasPrice		
12.22.	eth_getLogs		
12.30.	eth_getBalance		
12.32.	eth_getTransactionCount		
12.33.	eth_getCode		
12.35.	eth_sendRawTransaction		
12.36.	eth_getTransactionByHash		
12.39.	eth_getTransactionReceipt		
12.40.	eht_getStorageAt		
12.61.	web3_clientVersion		
12.63.	net_version
'''


@allure.story("Basic: Json-RPC call tests - transactions")
class TestRpcCallsTransactions(BasicTests):
    def test_rpc_call_eth_getTransactionCount(self, prepare_accounts):
        """Verify implemented rpc calls work eth_getTransactionCount"""

        self.process_transaction(self.sender_account, self.recipient_account,
                                 InputData.SAMPLE_AMOUNT.value)

        params = [self.sender_account.address, Tag.LATEST.value]
        model = RpcRequestFactory.get_trx_count(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(
            actual_result), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

    def test_rpc_call_eth_sendRawTransaction(self, prepare_accounts):
        """Verify implemented rpc calls work eth_sendRawTransaction"""

        transaction = {
            "from":
            self.sender_account.address,
            "to":
            self.recipient_account.address,
            "value":
            self.web3_client.toWei(InputData.SAMPLE_AMOUNT.value, "ether"),
            "chainId":
            self.web3_client._chain_id,
            "gasPrice":
            self.web3_client.gas_price(),
            "gas":
            0,
            "nonce":
            self.web3_client.eth.get_transaction_count(
                self.sender_account.address),
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)

        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]

        model = RpcRequestFactory.get_send_raw_trx(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(
            actual_result), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

        self.assert_balance(
            self.recipient_account.address,
            InputData.FAUCET_1ST_REQUEST_AMOUNT.value +
            InputData.SAMPLE_AMOUNT.value)

    def test_rpc_call_eth_getTransactionByHash(self, prepare_accounts):
        """Verify implemented rpc calls work eth_getTransactionByHash"""

        tx_receipt = self.process_transaction(self.sender_account,
                                              self.recipient_account,
                                              InputData.SAMPLE_AMOUNT.value)

        params = [tx_receipt.transactionHash.hex()]
        model = RpcRequestFactory.get_trx_by_hash(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(
            response, TrxResponse)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(
            actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(
            actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

    def test_rpc_call_eth_getTransactionReceipt(self, prepare_accounts):
        """Verify implemented rpc calls work eth_getTransactionReceipt"""

        tx_receipt = self.process_transaction(self.sender_account,
                                              self.recipient_account,
                                              InputData.SAMPLE_AMOUNT.value)

        params = [tx_receipt.transactionHash.hex()]
        model = RpcRequestFactory.get_trx_receipt(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(
            response, TrxReceiptResponse)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_no_error_object(
            actual_result), AssertMessage.CONTAINS_ERROR
        assert self.assert_result_object(
            actual_result), AssertMessage.DOES_NOT_CONTAIN_RESULT

        result_object = self.jsonrpc_requester.deserialize_response

    def test_check_erc_1820_transaction(self, prepare_accounts):
        """Check ERC-1820 transaction (without chain_id in sign)"""
        transaction = {
            "from":
            self.sender_account.address,
            "to":
            self.recipient_account.address,
            "value":
            self.web3_client.toWei(InputData.SAMPLE_AMOUNT.value, "ether"),
            "gasPrice":
            self.web3_client.gas_price(),
            "gas":
            0,
            "nonce":
            self.web3_client.eth.get_transaction_count(
                self.sender_account.address),
        }
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)

        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key)

        params = [signed_tx.rawTransaction.hex()]

        model = RpcRequestFactory.get_send_raw_trx(params=params)
        response = self.jsonrpc_requester.request_json_rpc(model)
        actual_result = self.jsonrpc_requester.deserialize_response(response)

        assert actual_result.id == model.id, AssertMessage.WRONG_ID.value
        assert self.assert_is_successful_response(
            actual_result), AssertMessage.WRONG_TYPE.value
        assert '0x' in actual_result.result, AssertMessage.DOES_NOT_START_WITH_0X.value

        self.assert_balance(
            self.recipient_account.address,
            InputData.FAUCET_1ST_REQUEST_AMOUNT.value +
            InputData.SAMPLE_AMOUNT.value)


@allure.story("Basic: Json-RPC call tests - transactions validation")
class TestRpcCallsTransactionsValidation(BasicTests):
    @pytest.mark.parametrize("gas_limit,gas_price,expected_message", GAS_LIMIT_AND_PRICE_DATA)
    def test_generate_bad_sign(self, gas_limit, gas_price, expected_message, prepare_accounts):
        """Generate bad sign (when v, r, s over allowed size)
        Too low gas_limit
        Too high gas_limit > u64::max
        Too high gas_limit > u64::max
        Too high gas_price > u64::max
        Too high gas_limit * gas_price > u64::max
        """

        amount = InputData.DEFAULT_TRANSFER_AMOUNT.value

        self.process_transaction_with_failure(
            self.sender_account,
            self.recipient_account,
            amount,
            gas=gas_limit,
            gas_price=gas_price,
            error_message=expected_message)

        self.assert_balance(self.sender_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
        self.assert_balance(self.recipient_account.address,
                            InputData.FAUCET_1ST_REQUEST_AMOUNT.value)
