import eth_abi
import pytest

from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from utils.consts import AccountType
from utils.types import Contract


@pytest.fixture(scope="session")
def recipients(evm_loader, operator_keypair):
    return [evm_loader.make_new_user(operator_keypair) for _ in range(12)]


@pytest.fixture(scope="session")
def distributor_contract(
    evm_loader, operator_keypair, session_user, neon_rpc_client, treasury_pool, holder_acc, recipients
):
    contract = evm_loader.deploy_contract(
        operator_keypair, session_user, "common/NeonDistributor", neon_rpc_client, treasury_pool, version="0.8.12"
    )
    names = [f"Name_{recipient.eth_address[0:4]}" for recipient in recipients]
    addresses = [recipient.eth_address for recipient in recipients]

    function_signature = "set_addresses(string[],address[])"
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=session_user.eth_address.hex(),
        contract=contract.eth_address.hex(),
        function_signature=function_signature,
        params=[names, addresses],
    )
    signed_tx = make_contract_call_trx(evm_loader, session_user, contract, function_signature, [names, addresses])
    evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
    evm_loader.execute_transaction_steps_from_account(operator_keypair, treasury_pool, holder_acc, emulate_accounts)
    return contract


@pytest.fixture(scope="session")
def distributor_caller_containerized(
    evm_loader,
    operator_keypair,
    neon_rpc_client,
    treasury_pool,
    distributor_contract,
    sender_with_tokens,
    recipients,
):
    constructor_args = eth_abi.encode(["address"], [distributor_contract.eth_address.hex()])

    contract = evm_loader.deploy_contract(
        operator_keypair,
        sender_with_tokens,
        "common/NeonDistributor",
        neon_rpc_client,
        treasury_pool,
        contract_name="NeonDistributorCaller",
        version="0.8.12",
        encoded_args=constructor_args,
    )
    function_signature = "distribute_value()"
    value = len(recipients) * 10
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=contract.eth_address.hex(),
        function_signature=function_signature,
        value=value,
    )

    data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
    balance_accounts = [
        contract.balance_account_address,
        distributor_contract.balance_account_address,
    ] + [recipient.balance_account_address for recipient in recipients]

    contract_accounts = [distributor_contract.solana_address]

    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=contract.solana_address,
        accounts=data_accounts + contract_accounts,
    )

    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=contract.solana_address,
        accounts=balance_accounts,
    )
    return contract


@pytest.fixture(scope="function")
def rw_lock_contract_new(
    evm_loader,
    operator_keypair,
    neon_rpc_client,
    session_user,
    treasury_pool,
) -> Contract:
    return evm_loader.deploy_contract(operator_keypair, session_user, "rw_lock", neon_rpc_client, treasury_pool)


@pytest.fixture(scope="session")
def rw_lock_contract_containerized(
    evm_loader, operator_keypair, neon_rpc_client, session_user, treasury_pool, holder_acc
) -> Contract:
    contract = evm_loader.deploy_contract(operator_keypair, session_user, "rw_lock", neon_rpc_client, treasury_pool)
    function_signature = "update_storage(uint256)"
    acc_count = 5

    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=session_user.eth_address.hex(),
        contract=contract.eth_address.hex(),
        function_signature=function_signature,
        params=[acc_count],
    )

    signed_tx = make_contract_call_trx(evm_loader, session_user, contract, function_signature, [acc_count])
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )

    data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=contract.solana_address,
        accounts=data_accounts,
    )

    return contract


@pytest.fixture(scope="function")
def rw_lock_contract_containerized_for_function(
    evm_loader, operator_keypair, neon_rpc_client, session_user, treasury_pool, holder_acc
) -> Contract:
    contract = evm_loader.deploy_contract(operator_keypair, session_user, "rw_lock", neon_rpc_client, treasury_pool)
    function_signature = "update_storage(uint256)"
    acc_count = 3

    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=session_user.eth_address.hex(),
        contract=contract.eth_address.hex(),
        function_signature=function_signature,
        params=[acc_count],
    )

    signed_tx = make_contract_call_trx(evm_loader, session_user, contract, function_signature, [acc_count])
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )

    data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=contract.solana_address,
        accounts=data_accounts,
    )

    return contract


@pytest.fixture(scope="session")
def revision_contract_containerized(
    evm_loader, operator_keypair, session_user, neon_rpc_client, treasury_pool, holder_acc
) -> Contract:
    contract = evm_loader.deploy_contract(
        operator_keypair,
        session_user,
        "common/Revision.sol",
        neon_rpc_client,
        treasury_pool,
        contract_name="RevisionChanger",
        version="0.8.12",
    )
    function_signature = "changeGlobalVarB(uint256)"
    value = 20

    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=session_user.eth_address.hex(),
        contract=contract.eth_address.hex(),
        function_signature=function_signature,
        params=[value],
    )

    signed_tx = make_contract_call_trx(evm_loader, session_user, contract, function_signature, [value])
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )

    data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=contract.solana_address,
        accounts=data_accounts,
    )

    return contract


@pytest.fixture(scope="function")
def storage_checker_containerized(
    evm_loader,
    neon_rpc_client,
    operator_keypair,
    session_user,
    treasury_pool,
) -> Contract:
    return evm_loader.deploy_contract(operator_keypair, session_user, "storage_checker", neon_rpc_client, treasury_pool)
