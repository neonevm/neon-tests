import inspect
from random import randint

import pytest
from _pytest.config import Config

from solders.keypair import Keypair as SolanaAccount
from web3.types import TxReceipt
from integration.tests.basic.helpers.basic import AccountData

from utils.tracer_client import TracerClient
from utils.storage_contract import StorageContract
from utils.accounts import EthAccounts
from utils.tracer_validator import TracerValidator
from utils.types import TransactionType
from utils.web3client import NeonChainWeb3Client


@pytest.fixture(scope="session")
def tracer_json_rpc_client_session(pytestconfig: Config):
    return TracerClient(pytestconfig.environment.tracer_url)


@pytest.fixture(scope="class")
def tracer_api(tracer_json_rpc_client_session, request):
    if inspect.isclass(request.cls):
        request.cls.tracer_api = tracer_json_rpc_client_session
    yield tracer_json_rpc_client_session


@pytest.fixture(scope="class")
def tracer_validator(request):
    validator = TracerValidator()
    if inspect.isclass(request.cls):
        request.cls.tracer_validator = validator
    yield validator


@pytest.fixture(scope="class")
def storage_object(web3_client, storage_contract):
    return StorageContract(web3_client, storage_contract)


@pytest.fixture(scope="class")
def send_neon_tx_receipt(accounts, web3_client) -> TxReceipt:
    sender, recipient = accounts[0], accounts[1]
    receipt = web3_client.send_neon(sender, recipient, 0.1)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def call_storage_tx_receipt(accounts, storage_object):
    sender_account = accounts[0]
    store_value = randint(1, 100)
    _, _, receipt = storage_object.call_storage(sender_account, store_value, "blockNumber")
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt, store_value


@pytest.fixture(scope="class")
def precompile_contract_call_tx_receipt(accounts, web3_client):
    input_data = "0x000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000040e09ad9675465c53a109fac66a445c91b292d2bb2c5268addb30cd82f80fcb0033ff97c80a5fc6f39193ae969c6ede6710a6b7ac27078a06d90ef1c72e5c85fb502fc9e1f6beb81516545975218075ec2af118cd8798df6e08a147c60fd6095ac2bb02c2908cf4dd7c81f11c289e4bce98f3553768f392a80ce22bf5c4f4a248c6b"
    address = "0x0000000000000000000000000000000000000005"
    sender_account = accounts[0]
    instruction_tx = web3_client.make_raw_tx(sender_account, address, estimate_gas=True, data=input_data)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def static_call_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.getBalanceOfContractCallee(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def static_call_with_events_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.emitEventAndGetBalanceOfContractCalleeWithEvents(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def call_with_events_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.lowLevelCallContractWithEvents(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def call_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.lowLevelCallContract(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def delegate_call_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.setParamWithDelegateCall(
        event_checker_callee_address, 9
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def callcode_tx_receipt(accounts, web3_client, opcodes_checker):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = opcodes_checker.functions.test_callcode().build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def zero_division_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.callNotSafeDivision(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def revert_with_assert_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.callContactRevertWithAssertFalse(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def trivial_revert_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.callContactTrivialRevert(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def revert_in_called_contract_tx_receipt(accounts, web3_client, events_checker_contract, event_checker_callee_address):
    sender_account = accounts[0]

    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.callContactRevertInsufficientBalance(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def call_contract_revert_with_require_tx_receipt(
    accounts, web3_client, events_checker_contract, event_checker_callee_address
):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.callContractRevertWithRequire(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def eth_precompile_contract_tx_receipt(accounts, web3_client, eip1052_checker):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(sender_account)
    precompiled_acc = AccountData(address="0xFf00000000000000000000000000000000000004")
    instruction_tx = eip1052_checker.functions.getContractHashWithLog(precompiled_acc.address).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1
    return receipt


@pytest.fixture(scope="class")
def call_contract_with_two_events_tx_receipt(
    accounts, web3_client, events_checker_contract, event_checker_callee_address
):
    sender_account = accounts[0]

    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = events_checker_contract.functions.emitAllEventsAndCallContractCalleeWithEvent(
        event_checker_callee_address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def call_contract_with_event_in_constructor_tx_receipt(accounts, web3_client, events_checker_contract):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = (
        events_checker_contract.functions.callChildWithEventAndContractCreationInConstructor().build_transaction(tx)
    )
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def precompiled_neon_contract_tx_receipt(web3_client: NeonChainWeb3Client, accounts: EthAccounts, neon_token_contract):
    tx_type = TransactionType(2)
    sender_account = accounts[0]
    sol_user = SolanaAccount()
    move_amount = web3_client._web3.to_wei(5, "ether")
    tx = web3_client.make_raw_tx(from_=sender_account, amount=move_amount, tx_type=tx_type)
    instruction_tx = neon_token_contract.functions.withdraw(bytes(sol_user.pubkey())).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1
    return receipt


@pytest.fixture(scope="class")
def trivial_error_tx_receipt(accounts, web3_client, revert_contract_caller):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(sender_account, gas=10000000)
    instruction_tx = revert_contract_caller.functions.doTrivialRevert().build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 0, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def event_tx_receipt(accounts, web3_client, event_caller_contract):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = event_caller_contract.functions.callEvent1("Event call").build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt
