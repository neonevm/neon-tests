import base58
import pytest
from eth_utils import abi, to_text

from utils.helpers import decode_error_output
from .utils.contract import get_contract_bin


def decode_pubkey(pubkey):
    return base58.b58encode(bytes(pubkey)).decode("utf-8")


def test_get_storage_at(neon_rpc_client, hello_world_contract):
    storage = neon_rpc_client.get_storage_at(hello_world_contract.eth_address.hex())
    zero_array = [0 for _ in range(31)]
    assert storage == zero_array + [5]

    storage = neon_rpc_client.get_storage_at(hello_world_contract.eth_address.hex(), index="0x2")
    assert storage == zero_array + [0]


def test_get_balance(neon_rpc_client, session_user, evm_loader):
    result = neon_rpc_client.get_balance(session_user.eth_address.hex())
    assert str(session_user.balance_account_address) == result["solana_address"]
    assert evm_loader.get_account_info(session_user.solana_account.pubkey()).value is not None


@pytest.mark.parametrize("account_info", [None, "Changed", "All"])
def test_emulate_transfer(neon_rpc_client, second_session_user, session_user, account_info):
    result = neon_rpc_client.emulate(
        second_session_user.eth_address.hex(), session_user.eth_address.hex(), provide_account_info=account_info
    )
    assert result["exit_status"] == "succeed", f"The 'exit_status' field is not succeed. Result: {result}"
    assert result["steps_executed"] == 1, f"Steps executed amount is not 1. Result: {result}"
    assert result["used_gas"] > 0, f"Used gas is less than 0. Result: {result}"
    assert "accounts_data" in result

    if account_info is None:
        assert result["accounts_data"] is None

    if account_info in ["Changed", "All"]:
        assert len(result["accounts_data"]) > 0
        assert len(result["solana_accounts"]) > 0

        all_accounts = [str(session_user.solana_account_address), str(second_session_user.balance_account_address)]
        writable_accounts = [str(second_session_user.balance_account_address)]

        actual_accounts = [decode_pubkey(account["pubkey"]) for account in result["accounts_data"]]

        if account_info == "Changed":
            assert set(actual_accounts) == set(writable_accounts)
            assert set(actual_accounts) != set(all_accounts)
            assert set(actual_accounts).issubset(set(all_accounts))
        elif account_info == "All":
            assert set(actual_accounts) == set(all_accounts)


def test_emulate_contract_deploy(neon_rpc_client, session_user):
    contract_code = get_contract_bin("hello_world")
    result = neon_rpc_client.emulate(session_user.eth_address.hex(), contract=None, data=contract_code)
    assert result["exit_status"] == "succeed", f"The 'exit_status' field is not succeed. Result: {result}"
    assert result["steps_executed"] > 100, f"Steps executed amount is wrong. Result: {result}"
    assert result["used_gas"] > 0, f"Used gas is less than 0. Result: {result}"


def test_emulate_call_contract_function(neon_rpc_client, session_user, hello_world_contract):
    data = abi.function_signature_to_4byte_selector("call_hello_world()")

    result = neon_rpc_client.emulate(
        session_user.eth_address.hex(), contract=hello_world_contract.eth_address.hex(), data=data
    )

    assert result["exit_status"] == "succeed", f"The 'exit_status' field is not succeed. Result: {result}"
    assert result["steps_executed"] > 0, f"Steps executed amount is 0. Result: {result}"
    assert result["used_gas"] > 0, f"Used gas is less than 0. Result: {result}"
    assert result["is_timestamp_number_used"] is False, f"Value for is_timestamp_number_used is wrong. Result: {result}"
    assert "Hello World" in to_text(result["result"])


def test_emulate_with_small_amount_of_steps(neon_rpc_client, session_user):
    contract_code = get_contract_bin("hello_world")
    result = neon_rpc_client.emulate(
        session_user.eth_address.hex(), contract=None, data=contract_code, max_steps_to_execute=10
    )
    assert result["exit_status"] == "revert", f"The 'exit_status' field is not revert. Result: {result}"


@pytest.mark.parametrize("contract_name", ["BlockTimestamp", "BlockNumber"])
def test_emulate_call_contract_with_block_timestamp_number(
    contract_name, neon_rpc_client, operator_keypair, treasury_pool, evm_loader, session_user
):
    contract = evm_loader.deploy_contract(
        operator_keypair,
        session_user,
        "common/Block.sol",
        neon_rpc_client,
        treasury_pool,
        contract_name=contract_name,
        version="0.8.10",
    )

    result = neon_rpc_client.emulate_contract_call(
        session_user.eth_address.hex(),
        contract=contract.eth_address.hex(),
        function_signature="addDataToMapping(uint256,uint256,uint256)",
        params=[1, 2, 20],
    )

    assert result["exit_status"] == "succeed", f"The 'exit_status' field is not succeed. Result: {result}"
    assert result["is_timestamp_number_used"], f"Timestamp number is not used. Result: {result}"


@pytest.mark.parametrize("contract_mapping_data_count", [75, 200])
def test_emulate_call_contract_with_account_limitation_negative(
    alt_contract,
    session_user,
    contract_mapping_data_count,
    neon_rpc_client,
):
    account_limit = 68
    result = neon_rpc_client.emulate_contract_call(
        session_user.eth_address.hex(),
        contract=alt_contract.eth_address.hex(),
        function_signature="fill(uint256)",
        params=[contract_mapping_data_count],
        account_limit=account_limit,
    )
    assert (
        result["exit_status"] == "revert"
    ), f"The trx is not reverted with account_limit={account_limit}. Trx account count is {len(result['solana_accounts'])}"
    assert f"Too many accounts: {account_limit + 1} > {account_limit}" in decode_error_output(result["result"])
