from integration.tests.basic.helpers.rpc_checks import is_hex


def test_get_contract(neon_rpc_client, rw_lock_contract_containerized, rw_lock_contract_new):
    resp_container = neon_rpc_client.get_contract(rw_lock_contract_containerized.eth_address.hex())
    resp_contract = neon_rpc_client.get_contract(rw_lock_contract_new.eth_address.hex())
    assert resp_container["solana_address"] == str(rw_lock_contract_containerized.solana_address)

    assert resp_container["code"] == resp_contract["code"]


def test_get_contract_for_contract_inside_container(
    neon_rpc_client, distributor_caller_containerized, distributor_contract
):
    resp = neon_rpc_client.get_contract(distributor_contract.eth_address.hex())
    assert resp["solana_address"] == str(distributor_contract.solana_address)
    assert is_hex(resp["code"])


def test_get_storage_at(revision_contract_containerized, evm_loader, neon_rpc_client):
    zero_array = [0] * 31
    storage = neon_rpc_client.get_storage_at(revision_contract_containerized.eth_address.hex(), index="0x0")
    assert storage == zero_array + [1]

    storage = neon_rpc_client.get_storage_at(revision_contract_containerized.eth_address.hex(), index="0x1")
    assert storage == zero_array + [20]


def test_get_balance_for_container(neon_rpc_client, session_user, evm_loader, revision_contract_containerized):
    resp = neon_rpc_client.get_balance(revision_contract_containerized.eth_address.hex())
    assert resp["solana_address"] == str(revision_contract_containerized.balance_account_address)
    assert resp["trx_count"] >= 1


def test_get_balance_for_user_in_container(
    neon_rpc_client,
    session_user,
    evm_loader,
    distributor_caller_containerized,
    operator_keypair,
    user_account,
    treasury_pool,
):
    container_address = distributor_caller_containerized.solana_address

    evm_loader.deposit_neon(operator_keypair, user_account.eth_address, 1)
    evm_loader.assemble_container(
        operator_keypair, treasury_pool, container_address, [user_account.balance_account_address]
    )
    balance = int(neon_rpc_client.get_balance(user_account.eth_address.hex())["balance"], 16)
    assert balance == 1 * 10**9


def test_get_container(
    neon_rpc_client, distributor_caller_containerized, evm_loader, operator_keypair, user_account, treasury_pool
):
    container_address = distributor_caller_containerized.solana_address
    container_accounts_before = neon_rpc_client.get_container_accounts(container_address)
    evm_loader.assemble_container(
        operator_keypair, treasury_pool, container_address, [user_account.balance_account_address]
    )
    container_accounts_after = neon_rpc_client.get_container_accounts(container_address)
    assert len(container_accounts_after) == len(container_accounts_before) + 1
