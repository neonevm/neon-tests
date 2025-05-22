import inspect
import random

import pytest
from _pytest.config import Config

from solders.keypair import Keypair as SolanaAccount
from spl.token.constants import WRAPPED_SOL_MINT
from web3.types import TxReceipt
from integration.tests.basic.helpers.basic import AccountData
from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from utils.helpers import decode_function_signature, wait_condition
from utils.scheduled_trx import ScheduledTrxEstimateRequest, ScheduledTransaction, CreateTreeAccMultipleData

from utils.tracer_client import TracerClient
from utils.storage_contract import StorageContract
from utils.accounts import EthAccounts
from utils.tracer_validator import TracerValidator
from utils.types import TransactionType
from utils.web3client import NeonChainWeb3Client, BASE_MAX_PRIORITY_FEE


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
    store_value = random.randint(1, 100)
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


@pytest.fixture(scope="class")
def scheduled_tx_receipt(web3_client_sol, neon_user_for_session, common_contract, evm_loader, treasury_pool):
    contract_data = 18
    data = decode_function_signature("setNumber(uint256)", [contract_data])
    trx_estimate_obj = ScheduledTrxEstimateRequest(
        neon_user_for_session.checksum_address, common_contract.address, data
    )
    estimate_result = web3_client_sol.estimate_scheduled(
        neon_user_for_session.solana_account.pubkey(), [trx_estimate_obj]
    )
    tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

    evm_loader.create_tree_account(
        neon_user_for_session, treasury_pool, tx.encode(), WRAPPED_SOL_MINT, chain_id=evm_loader.sol_chain_id
    )
    check_trx_is_success(web3_client_sol, evm_loader, tx.hash().hex())
    receipt = web3_client_sol.wait_for_transaction_receipt(tx.hash().hex())
    return receipt


@pytest.fixture(scope="class")
def multiple_scheduled_tx_receipts(
    web3_client_sol, neon_user_for_session, common_contract, evm_loader, treasury_pool
) -> list[TxReceipt]:
    data = decode_function_signature("setNumber(uint256)", [10])

    trx_estimate_obj_list = []
    for i in range(3):
        trx_estimate_obj_list.append(
            ScheduledTrxEstimateRequest(
                neon_user_for_session.checksum_address, common_contract.address, data, child_transaction=hex(3)
            )
        )
    trx_estimate_obj_list.append(
        ScheduledTrxEstimateRequest(
            neon_user_for_session.checksum_address, common_contract.address, data, child_transaction="0xFFFF"
        )
    )
    estimate_result = web3_client_sol.estimate_scheduled(
        neon_user_for_session.solana_account.pubkey(), trx_estimate_obj_list
    )
    trxs = []
    for i in range(4):
        trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

    tree_acc_data = CreateTreeAccMultipleData(
        nonce=estimate_result["nonce"],
        max_fee_per_gas=estimate_result["maxFeePerGas"],
        max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
    )

    tree_acc_data.add_trx(trxs[0], 3, 0)
    tree_acc_data.add_trx(trxs[1], 3, 0)
    tree_acc_data.add_trx(trxs[2], 3, 0)
    tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)

    evm_loader.create_tree_account_multiple(
        neon_user_for_session,
        treasury_pool,
        tree_acc_data.data,
        WRAPPED_SOL_MINT,
    )
    web3_client_sol.send_all_scheduled_transactions(trxs)
    receipts = []
    for tx in trxs:
        check_trx_is_success(web3_client_sol, evm_loader, tx.hash().hex(), timeout=180)
        receipt = web3_client_sol.wait_for_transaction_receipt(tx.hash().hex())
        receipts.append(receipt)
    return receipts


@pytest.fixture(scope="class")
def recursion_tx_receipt(accounts, web3_client):

    sender_account = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract(
        "common/Recursion",
        "0.8.10",
        sender_account,
        contract_name="DeployRecursionFactory",
        constructor_args=[3],
    )

    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(sender_account)
    instruction_tx = contract.functions.deployFirstContract().build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1
    assert contract.functions.getFirstDeployedContractCount().call() == 3
    return receipt


@pytest.fixture(scope="class")
def iteration_tx_receipt(accounts, web3_client, counter_contract):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)

    wait_condition(
        lambda: web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
        timeout_sec=120,
    )
    assert receipt["status"] == 1
    return receipt


@pytest.fixture(scope="class")
def iterative_tx_with_erc20_for_spl_receipt(accounts, web3_client, multiple_actions_erc20):
    sender_account = accounts[0]
    acc, contract = multiple_actions_erc20
    mint_amount1 = random.randint(10, 100000000)
    mint_amount2 = random.randint(10, 100000000)

    tx = web3_client.make_raw_tx(sender_account)
    instruction_tx = contract.functions.mintMintTransferTransferMintMintTransferTransfer(
        mint_amount1, mint_amount2, acc.address
    ).build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)

    wait_condition(
        lambda: web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
        timeout_sec=120,
    )
    assert receipt["status"] == 1
    return receipt


@pytest.fixture(scope="class")
def chain_transactions_receipt_and_contracts(accounts, web3_client, chain_execution_contracts):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = chain_execution_contracts[0].functions.start_execution().build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt, chain_execution_contracts


@pytest.fixture(scope="class")
def failed_scheduled_tx_receipt(
    web3_client_sol, neon_user_for_session, treasury_pool, revert_contract_caller, event_caller_contract, evm_loader
):
    nonce = web3_client_sol.get_nonce(neon_user_for_session.checksum_address)

    max_priority_fee_per_gas = BASE_MAX_PRIORITY_FEE
    max_fee_per_gas = web3_client_sol.get_max_fee_per_gas()
    gas_limit = 30000000

    call_data_trx0 = decode_function_signature("doAssert()")

    tx = ScheduledTransaction(
        neon_user_for_session.neon_address,
        None,
        nonce,
        index=0,
        target=revert_contract_caller.address,
        call_data=call_data_trx0,
        max_fee_per_gas=max_fee_per_gas,
        max_priority_fee_per_gas=max_priority_fee_per_gas,
        gas_limit=gas_limit,
        chain_id=web3_client_sol.chain_id,
    )

    tree_acc_data = CreateTreeAccMultipleData(
        nonce=nonce, max_fee_per_gas=max_fee_per_gas, max_priority_fee_per_gas=max_priority_fee_per_gas
    )
    tree_acc_data.add_trx(tx, 0xFFFF, 0)
    evm_loader.create_tree_account_multiple(neon_user_for_session, treasury_pool, tree_acc_data.data)

    web3_client_sol.send_all_scheduled_transactions([tx])

    receipt = web3_client_sol.wait_for_transaction_receipt(tx.hash().hex())
    return receipt


@pytest.fixture(scope="class")
def reverted_iterative_tx_receipt(accounts, web3_client, revert_contract_caller):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(sender_account, gas=10000000)
    instruction_tx = revert_contract_caller.functions.doTrivialRevertAferIterativeActions().build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 0
    return receipt


@pytest.fixture(scope="class")
def canceled_tx_with_hash_receipt(accounts, web3_client, expected_error_checker):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(sender_account)
    instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 0, f"Transaction success: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def canceled_iterative_tx_with_hash_receipt(accounts, web3_client, expected_error_checker):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(sender_account)
    instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 0, f"Transaction success: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def transaction_return_data_receipt(accounts, web3_client, common_contract):
    sender_account = accounts[0]
    test_text = "check_tracer_trace_transaction"
    tx_1 = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx_1 = common_contract.functions.setText(test_text).build_transaction(tx_1)
    web3_client.send_transaction(sender_account, instruction_tx_1)

    tx_2 = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx_2 = common_contract.functions.getText().build_transaction(tx_2)
    receipt = web3_client.send_transaction(sender_account, instruction_tx_2)
    assert receipt["status"] == 1, f"Transaction failed:{receipt}"
    return receipt, test_text


@pytest.fixture(scope="class")
def chain_with_revert_receipt(accounts, web3_client, chain_execution_contracts_with_revert):
    sender_account = accounts[0]
    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = (
        chain_execution_contracts_with_revert[0]
        .functions.execute_trivial_revert(chain_execution_contracts_with_revert[2].address)
        .build_transaction(tx)
    )
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt


@pytest.fixture(scope="class")
def chain_with_revert_in_middle_call_receipt_and_contracts(
    accounts, web3_client, chain_execution_contracts_with_revert
):
    sender_account = accounts[0]
    test_text = "check_revert_after_return_data"
    tx_1 = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx_1 = chain_execution_contracts_with_revert[3].functions.setText(test_text).build_transaction(tx_1)
    web3_client.send_transaction(sender_account, instruction_tx_1)

    tx = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx = (
        chain_execution_contracts_with_revert[0]
        .functions.execute_revert_in_middle_call(
            chain_execution_contracts_with_revert[3].address,
            chain_execution_contracts_with_revert[2].address,
        )
        .build_transaction(tx)
    )
    receipt = web3_client.send_transaction(sender_account, instruction_tx)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt, test_text


@pytest.fixture(scope="class")
def chain_with_return_data_receipt_and_contracts(accounts, web3_client, chain_execution_contracts_with_return_data):
    sender_account = accounts[0]
    test_text = "check_return_data_iteration_in_chain"
    tx_1 = web3_client.make_raw_tx(from_=sender_account)
    instruction_tx_1 = (
        chain_execution_contracts_with_return_data[2].functions.setText(test_text).build_transaction(tx_1)
    )
    web3_client.send_transaction(sender_account, instruction_tx_1)

    tx_2 = web3_client.make_raw_tx(from_=sender_account, amount=1001)
    instruction_tx_2 = (
        chain_execution_contracts_with_return_data[0]
        .functions.start_chain_with_return_data(chain_execution_contracts_with_return_data[2].address)
        .build_transaction(tx_2)
    )
    receipt = web3_client.send_transaction(sender_account, instruction_tx_2)
    assert receipt["status"] == 1, f"Transaction failed: {receipt}"
    return receipt, test_text
