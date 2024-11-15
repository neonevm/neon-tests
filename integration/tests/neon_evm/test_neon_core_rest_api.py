import base58
import pytest
from eth_utils import abi, to_text

from .utils.contract import deploy_contract, get_contract_bin


def decode_pubkey(pubkey):
    return base58.b58encode(bytes(pubkey)).decode("utf-8")


def test_get_storage_at(neon_api_client, operator_keypair, user_account, evm_loader, treasury_pool):
    contract = deploy_contract(operator_keypair, user_account, "hello_world", evm_loader, treasury_pool)
    storage = neon_api_client.get_storage_at(contract.eth_address.hex())["value"]
    zero_array = [0 for _ in range(31)]
    assert storage == zero_array + [5]

    storage = neon_api_client.get_storage_at(contract.eth_address.hex(), index="0x2")["value"]
    assert storage == zero_array + [0]


def test_get_balance(neon_api_client, user_account, evm_loader):
    result = neon_api_client.get_balance(user_account.eth_address.hex())["value"]
    assert str(user_account.balance_account_address) == result[0]["solana_address"]
    assert evm_loader.get_account_info(user_account.solana_account.pubkey()).value is not None


@pytest.mark.parametrize("account_info", [None, "Changed", "All"])
def test_emulate_transfer(neon_api_client, user_account, session_user, account_info):
    result = neon_api_client.emulate(
        user_account.eth_address.hex(), session_user.eth_address.hex(), provide_account_info=account_info
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

        all_accounts = [str(session_user.solana_account_address), str(user_account.balance_account_address)]
        writable_accounts = [str(user_account.balance_account_address)]

        actual_accounts = [decode_pubkey(account["pubkey"]) for account in result["accounts_data"]]

        if account_info == "Changed":
            assert set(actual_accounts) == set(writable_accounts)
            assert set(actual_accounts) != set(all_accounts)
            assert set(actual_accounts).issubset(set(all_accounts))
        elif account_info == "All":
            assert set(actual_accounts) == set(all_accounts)


def test_emulate_contract_deploy(neon_api_client, user_account):
    contract_code = get_contract_bin("hello_world")
    result = neon_api_client.emulate(user_account.eth_address.hex(), contract=None, data=contract_code)
    assert result["exit_status"] == "succeed", f"The 'exit_status' field is not succeed. Result: {result}"
    assert result["steps_executed"] > 100, f"Steps executed amount is wrong. Result: {result}"
    assert result["used_gas"] > 0, f"Used gas is less than 0. Result: {result}"


def test_emulate_call_contract_function(neon_api_client, operator_keypair, treasury_pool, evm_loader, user_account):
    contract = deploy_contract(operator_keypair, user_account, "hello_world", evm_loader, treasury_pool)
    assert contract.eth_address
    data = abi.function_signature_to_4byte_selector("call_hello_world()")

    result = neon_api_client.emulate(user_account.eth_address.hex(), contract=contract.eth_address.hex(), data=data)

    assert result["exit_status"] == "succeed", f"The 'exit_status' field is not succeed. Result: {result}"
    assert result["steps_executed"] > 0, f"Steps executed amount is 0. Result: {result}"
    assert result["used_gas"] > 0, f"Used gas is less than 0. Result: {result}"
    assert result["is_timestamp_number_used"] is False, f"Value for is_timestamp_number_used is wrong. Result: {result}"
    assert "Hello World" in to_text(result["result"])


def test_emulate_with_small_amount_of_steps(neon_api_client, evm_loader, user_account):
    contract_code = get_contract_bin("hello_world")
    result = neon_api_client.emulate(
        user_account.eth_address.hex(), contract=None, data=contract_code, max_steps_to_execute=10
    )
    assert result["exit_status"] == "revert", f"The 'exit_status' field is not revert. Result: {result}"


@pytest.mark.parametrize("contract_name", ["BlockTimestamp", "BlockNumber"])
def test_emulate_call_contract_with_block_timestamp_number(contract_name, neon_api_client, operator_keypair,
                                                           treasury_pool, evm_loader):
    user_account = evm_loader.make_new_user(operator_keypair)
    contract = deploy_contract(
        operator_keypair,
        user_account,
        "common/Block.sol",
        evm_loader,
        treasury_pool,
        version="0.8.10",
        contract_name=contract_name,
    )

    result = neon_api_client.emulate_contract_call(user_account.eth_address.hex(),
                                                   contract=contract.eth_address.hex(),
                                                   function_signature="addDataToMapping(uint256,uint256)",
                                                   params=[1, 2])

    assert result["exit_status"] == "succeed", f"The 'exit_status' field is not succeed. Result: {result}"
    assert result["is_timestamp_number_used"], f"Timestamp number is not used. Result: {result}"
