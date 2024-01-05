from eth_utils import abi, to_text

from utils.consts import ZERO_HASH, LAMPORT_PER_SOL
from .utils.constants import CHAIN_ID
from .utils.contract import deploy_contract, get_contract_bin
from .solana_utils import solana_client, write_transaction_to_holder_account, deposit_neon
from .utils.ethereum import make_eth_transaction
from .utils.storage import create_holder


def test_get_storage_at(neon_rpc_client, operator_keypair, user_account, evm_loader, treasury_pool):
    contract = deploy_contract(operator_keypair, user_account, "hello_world", evm_loader, treasury_pool)
    storage = neon_rpc_client.get_storage_at(contract.eth_address.hex(), index='0x0')
    zero_array = [0 for _ in range(31)]
    assert storage == zero_array + [5]
    storage = neon_rpc_client.get_storage_at(contract.eth_address.hex(), index='0x2')
    assert storage == zero_array + [0]


def test_get_balance(neon_rpc_client, user_account, sol_client, evm_loader, operator_keypair):
    result = neon_rpc_client.get_balance(user_account.eth_address.hex())
    assert str(user_account.balance_account_address) == result[0]["solana_address"]
    assert solana_client.get_account_info(user_account.solana_account.public_key).value is not None
    assert result[0]["status"] == 'Ok'
    assert result[0]["balance"] == '0x0'
    amount = 100000
    deposit_neon(evm_loader, operator_keypair, user_account.eth_address, amount)
    result = neon_rpc_client.get_balance(user_account.eth_address.hex())
    assert result[0]["balance"] == hex(amount * LAMPORT_PER_SOL)


def test_emulate_transfer(neon_rpc_client, user_account, session_user):
    result = neon_rpc_client.emulate(user_account.eth_address.hex(),
                                     session_user.eth_address.hex())
    assert result['exit_status'] == 'succeed', f"The 'exit_status' field is not succeed. Result: {result}"
    assert result['steps_executed'] == 1, f"Steps executed amount is not 1. Result: {result}"
    assert result['used_gas'] > 0, f"Used gas is less than 0. Result: {result}"


def test_emulate_contract_deploy(neon_rpc_client, user_account):
    contract_code = get_contract_bin("hello_world")
    result = neon_rpc_client.emulate(user_account.eth_address.hex(),
                                     contract=None, data=contract_code)
    assert result['exit_status'] == 'succeed', f"The 'exit_status' field is not succeed. Result: {result}"
    assert result['steps_executed'] > 100, f"Steps executed amount is wrong. Result: {result}"
    assert result['used_gas'] > 0, f"Used gas is less than 0. Result: {result}"


def test_emulate_call_contract_function(neon_rpc_client, operator_keypair, treasury_pool, evm_loader, user_account):
    contract = deploy_contract(operator_keypair, user_account, "hello_world", evm_loader, treasury_pool)
    data = abi.function_signature_to_4byte_selector('call_hello_world()')

    result = neon_rpc_client.emulate(user_account.eth_address.hex(),
                                     contract=contract.eth_address.hex(), data=data)

    assert result['exit_status'] == 'succeed', f"The 'exit_status' field is not succeed. Result: {result}"
    assert result['steps_executed'] > 0, f"Steps executed amount is 0. Result: {result}"
    assert result['used_gas'] > 0, f"Used gas is less than 0. Result: {result}"
    assert "Hello World" in to_text(result["result"])


def test_emulate_with_small_amount_of_steps(neon_rpc_client, evm_loader, user_account):
    contract_code = get_contract_bin("hello_world")
    result = neon_rpc_client.emulate(user_account.eth_address.hex(),
                                     contract=None, data=contract_code, max_steps_to_execute=10)
    assert result['message'] == 'Too many steps'


def test_get_contract(neon_rpc_client, rw_lock_contract):
    result = neon_rpc_client.get_contract(rw_lock_contract.eth_address.hex())[0]
    assert result['solana_address'] == str(rw_lock_contract.solana_address)
    assert result['chain_id'] == CHAIN_ID
    assert result['code'] != ""


def test_get_holder(neon_rpc_client, operator_keypair, session_user, sender_with_tokens):
    holder_acc = create_holder(operator_keypair)
    result = neon_rpc_client.get_holder(holder_acc)
    assert result["owner"] == str(operator_keypair.public_key)
    assert result["status"] == 'Holder'
    assert result["tx"] == ZERO_HASH

    signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 10)
    write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

    result = neon_rpc_client.get_holder(holder_acc)
    assert result["owner"] == str(operator_keypair.public_key)
    assert result["status"] == 'Holder'
    assert result["tx"] != ZERO_HASH


def test_collect_treasury(neon_rpc_client):
    result = neon_rpc_client.collect_treasury()
    assert result["pool_address"] != ""
    assert result["balance"] > 0


def test_get_config(neon_rpc_client):
    result = neon_rpc_client.get_config()
    assert CHAIN_ID in [item['id'] for item in result["chains"]]
    expected_fields = ["NEON_ACCOUNT_SEED_VERSION",
                       "NEON_EVM_STEPS_LAST_ITERATION_MAX",
                       "NEON_EVM_STEPS_MIN",
                       "NEON_GAS_LIMIT_MULTIPLIER_NO_CHAINID",
                       "NEON_HOLDER_MSG_SIZE",
                       "NEON_OPERATOR_PRIORITY_SLOTS",
                       "NEON_PAYMENT_TO_TREASURE",
                       "NEON_STORAGE_ENTRIES_IN_CONTRACT_ACCOUNT",
                       "NEON_TREASURY_POOL_COUNT",
                       "NEON_TREASURY_POOL_SEED"]
    for field in expected_fields:
        assert field in result["config"]
