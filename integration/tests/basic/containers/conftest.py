import pytest

from utils.solana_data_for_neon_trx_helper import get_accounts_for_container_by_emulation


@pytest.fixture(scope="class")
def alt_contract(accounts, web3_client):
    contract, _ = web3_client.deploy_and_get_contract("common/ALT", "0.8.10", account=accounts[0], constructor_args=[8])
    return contract


@pytest.fixture(scope="class")
def rw_lock_contract_containerized(evm_loader, solana_account, treasury_pool, web3_client, accounts, operator):
    sender = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract("neon_evm/rw_lock", "0.8.10", account=sender)

    tx = web3_client.make_raw_tx(accounts[0])
    instruction_tx = contract.functions.update_storage(20).build_transaction(tx)
    container_address = evm_loader.ether2program(contract.address[2:])

    accounts = get_accounts_for_container_by_emulation(
        web3_client, evm_loader, instruction_tx, sender, container_address
    )

    web3_client.send_transaction(sender, instruction_tx)

    evm_loader.assemble_container(
        operator=operator.operator_keypairs[0],
        treasury=treasury_pool,
        container_address=container_address,
        accounts=accounts,
    )
    return contract


@pytest.fixture(scope="class")
def distributor_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/NeonDistributor.sol",
        version="0.8.12",
        account=accounts[0],
    )
    return contract


@pytest.fixture(scope="class")
def alt_contract_containerized(accounts, web3_client, evm_loader, operator, treasury_pool):
    contract, _ = web3_client.deploy_and_get_contract(
        "common/ALT", "0.8.10", account=accounts[1], constructor_args=[50]
    )

    container_address = evm_loader.ether2program(contract.address[2:])
    tx = web3_client.make_raw_tx(accounts[1].address)
    instruction_tx = contract.functions.fill(30).build_transaction(tx)
    sol_accounts = get_accounts_for_container_by_emulation(
        web3_client, evm_loader, instruction_tx, accounts[1], container_address
    )

    evm_loader.assemble_container(operator.operator_keypairs[0], treasury_pool, container_address, sol_accounts)

    return contract


@pytest.fixture(scope="class")
def account_in_container(alt_contract_containerized, accounts):
    return accounts[1]  # Assuming the account is the one in the container in alt_contract_containerized
