import pytest
from solders.keypair import Keypair

from integration.tests.neon_evm.utils.constants import TAG_FINALIZED_STATE
from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import (
    check_transaction_logs_have_text,
    check_holder_account_tag,
)
from utils.consts import ExecuteTrxTypes, AccountType
from utils.neon_layouts.balance_account import BalanceAccount
from utils.neon_layouts.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT


def test_assemble_and_allocate_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    rw_lock_contract_containerized,
    holder_acc,
):
    function_signature = "update_storage(uint256)"
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract_containerized.eth_address.hex(),
        function_signature=function_signature,
        params=[10],
    )
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [10]
    )
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )
    data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
    # assemble container and execute transaction with it
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized.solana_address,
        accounts=data_accounts,
    )
    container_data_len_before = len(evm_loader.get_solana_account_data(rw_lock_contract_containerized.solana_address))

    # allocate container and execute transaction with it
    size = 256
    evm_loader.allocate_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized.solana_address,
        size=size,
    )
    container_data_len_after = len(evm_loader.get_solana_account_data(rw_lock_contract_containerized.solana_address))
    assert (
        container_data_len_after == container_data_len_before + size
    ), "Container data length did not increase after allocation"
    accounts_for_execution_with_container = [
        rw_lock_contract_containerized.solana_address,
        sender_with_tokens.solana_account_address,
        sender_with_tokens.balance_account_address,
    ]
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [10]
    )
    resp = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        accounts_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")


def test_disassemble_not_allocated_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    rw_lock_contract_containerized_for_function,
    holder_acc,
):
    function_signature = "update_storage(uint256)"
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract_containerized_for_function.eth_address.hex(),
        function_signature=function_signature,
        params=[10],
    )
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized_for_function, function_signature, [10]
    )
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )
    data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
    accounts_len_before_assemble = len(
        neon_rpc_client.get_container_accounts(rw_lock_contract_containerized_for_function.solana_address)
    )

    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized_for_function.solana_address,
        accounts=data_accounts,
    )
    data_len_before = len(
        evm_loader.get_solana_account_data(rw_lock_contract_containerized_for_function.solana_address)
    )

    accounts_len_before_disassemble = len(
        neon_rpc_client.get_container_accounts(rw_lock_contract_containerized_for_function.solana_address)
    )
    evm_loader.disassemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized_for_function.solana_address,
        accounts=data_accounts,
    )

    data_len_after = len(evm_loader.get_solana_account_data(rw_lock_contract_containerized_for_function.solana_address))
    accounts_len_after_disassemble = len(
        neon_rpc_client.get_container_accounts(rw_lock_contract_containerized_for_function.solana_address)
    )

    assert data_len_after < data_len_before
    assert accounts_len_before_assemble == accounts_len_after_disassemble
    assert accounts_len_after_disassemble < accounts_len_before_disassemble


def test_disassemble_container_fully(
    evm_loader,
    operator_keypair,
    treasury_pool,
    neon_rpc_client,
    session_user,
    holder_acc,
):
    contract = evm_loader.deploy_contract(operator_keypair, session_user, "rw_lock", neon_rpc_client, treasury_pool)
    function_signature = "update_storage(uint256)"
    acc_count = 1

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

    data_account = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)

    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=contract.solana_address,
        accounts=data_account,
    )

    accounts_before = neon_rpc_client.get_container_accounts(contract.solana_address)

    key_1 = str(contract.solana_address)
    key_2 = str(data_account[0])

    assert (key_1 in accounts_before[0]["pubkey"]) or (key_1 in accounts_before[1]["pubkey"])
    assert (key_2 in accounts_before[0]["pubkey"]) or (key_2 in accounts_before[1]["pubkey"])
    assert len(accounts_before) == 2

    data_len_before = len(evm_loader.get_solana_account_data(contract.solana_address))

    evm_loader.disassemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=contract.solana_address,
        accounts=data_account,
    )

    data_len_after = len(evm_loader.get_solana_account_data(contract.solana_address))
    accounts_len_after = len(neon_rpc_client.get_container_accounts(contract.solana_address))

    assert data_len_after < data_len_before
    assert accounts_len_after == 0


def test_assemble_allocate_and_disassemble_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    rw_lock_contract_containerized_for_function,
    holder_acc,
):
    accounts_len_before_assemble = len(
        neon_rpc_client.get_container_accounts(rw_lock_contract_containerized_for_function.solana_address)
    )

    function_signature = "update_storage(uint256)"
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract_containerized_for_function.eth_address.hex(),
        function_signature=function_signature,
        params=[10],
    )
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized_for_function, function_signature, [10]
    )
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )
    data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
    # assemble container and execute transaction with it
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized_for_function.solana_address,
        accounts=data_accounts,
    )
    data_len_before = len(
        evm_loader.get_solana_account_data(rw_lock_contract_containerized_for_function.solana_address)
    )

    accounts_len_after_assemble = len(
        neon_rpc_client.get_container_accounts(rw_lock_contract_containerized_for_function.solana_address)
    )
    assert accounts_len_after_assemble > accounts_len_before_assemble

    # allocate container and execute transaction with it
    size = 256
    evm_loader.allocate_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized_for_function.solana_address,
        size=size,
    )
    data_len_after = len(evm_loader.get_solana_account_data(rw_lock_contract_containerized_for_function.solana_address))
    assert data_len_after == data_len_before + size, "Container data length did not increase after allocation"
    accounts_for_execution_with_container = [
        rw_lock_contract_containerized_for_function.solana_address,
        sender_with_tokens.solana_account_address,
        sender_with_tokens.balance_account_address,
    ]
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized_for_function, function_signature, [10]
    )
    resp = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        accounts_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

    evm_loader.disassemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized_for_function.solana_address,
        accounts=data_accounts,
    )

    data_len_after_disassemble = len(
        evm_loader.get_solana_account_data(rw_lock_contract_containerized_for_function.solana_address)
    )
    assert data_len_after > data_len_after_disassemble, "Container data length did not decrease after disassembling"

    accounts_len_after_disassemble = len(
        neon_rpc_client.get_container_accounts(rw_lock_contract_containerized_for_function.solana_address)
    )
    assert accounts_len_after_disassemble == accounts_len_before_assemble


def test_deposit_neons_to_account_and_disassemble_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    neon_rpc_client,
    rw_lock_contract_containerized_for_function,
    user_account,
):
    evm_loader.assemble_container(
        operator_keypair,
        treasury_pool,
        rw_lock_contract_containerized_for_function.solana_address,
        [user_account.balance_account_address],
    )
    deposit_amount = 5000
    evm_loader.deposit_neon(
        operator_keypair,
        user_account.eth_address.hex(),
        deposit_amount,
        rw_lock_contract_containerized_for_function.solana_address,
    )

    balance_data = neon_rpc_client.get_account_data_from_container(
        rw_lock_contract_containerized_for_function.solana_address, user_account.balance_account_address
    )
    balance_account = BalanceAccount(balance_data)

    assert balance_account.balance == deposit_amount * 10**9, "Balance after deposit is incorrect"

    evm_loader.disassemble_container(
        operator_keypair,
        treasury_pool,
        rw_lock_contract_containerized_for_function.solana_address,
        [user_account.balance_account_address],
    )

    balance_data = neon_rpc_client.get_account_data_from_container(
        rw_lock_contract_containerized_for_function.solana_address, user_account.balance_account_address
    )
    assert balance_data is None

    balance_after_disassemble = evm_loader.get_neon_balance(user_account.eth_address.hex())
    assert balance_after_disassemble == deposit_amount * 10**9, "Balance after container disassembling is incorrect"


@pytest.mark.parametrize("execution_type", list(ExecuteTrxTypes))
def test_execute_trx_with_containerized_contract(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    distributor_caller_containerized,
    holder_acc,
    recipients,
    execution_type,
):
    function_signature = "distribute_value()"
    value = len(recipients) * 10
    container_address = distributor_caller_containerized.solana_address
    recipient_balance_acc_data = neon_rpc_client.get_account_data_from_container(
        container_address, recipients[0].balance_account_address
    )
    recipient_balance_before = BalanceAccount(recipient_balance_acc_data).balance

    accounts_for_execution_with_container = [
        container_address,
        sender_with_tokens.solana_account_address,
        sender_with_tokens.balance_account_address,
    ] + [recipient.solana_account_address for recipient in recipients]

    chain_id = None if execution_type == ExecuteTrxTypes.ITERATIVE_FROM_ACCOUNT_NO_CHAIN_ID else evm_loader.chain_id
    signed_tx = make_contract_call_trx(
        evm_loader,
        sender_with_tokens,
        distributor_caller_containerized,
        function_signature,
        value=value,
        chain_id=chain_id,
    )

    resp = evm_loader.execute_neon_trx(
        execution_type, signed_tx, operator_keypair, holder_acc, treasury_pool, accounts_for_execution_with_container
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

    recipient_balance_acc_data = neon_rpc_client.get_account_data_from_container(
        container_address, recipients[0].balance_account_address
    )
    recipient_balance_after = BalanceAccount(recipient_balance_acc_data).balance

    assert recipient_balance_after == recipient_balance_before + value / len(recipients)


def test_assemble_new_additional_accounts_from_emulation_many_times(
    evm_loader,
    operator_keypair,
    treasury_pool,
    sender_with_tokens,
    neon_rpc_client,
    rw_lock_contract_containerized,
    holder_acc,
):
    function_signature = "update_storage(uint256)"
    for acc_count in [20, 40, 60, 80]:
        emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=rw_lock_contract_containerized.eth_address.hex(),
            function_signature=function_signature,
            params=[acc_count],
        )

        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
        )
        evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
        )

        data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
        evm_loader.assemble_container(
            operator=operator_keypair,
            treasury=treasury_pool,
            container_address=rw_lock_contract_containerized.solana_address,
            accounts=data_accounts,
        )

        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                rw_lock_contract_containerized.solana_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )

        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")


def test_2_parallel_trx_with_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    holder_acc,
    second_holder_acc,
    rw_lock_contract_containerized,
    sender_with_tokens,
    session_user,
    neon_rpc_client,
):
    acc_count = 15
    function_signature = "update_storage(uint256)"
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract_containerized.eth_address.hex(),
        function_signature=function_signature,
        params=[acc_count],
    )
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
    )
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_tx, emulate_accounts
    )
    data_accounts = evm_loader.filter_neon_accounts_by_type(emulate_accounts, AccountType.STORAGE)
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized.solana_address,
        accounts=data_accounts + [rw_lock_contract_containerized.balance_account_address],
    )
    signed_tx = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
    )
    emulate_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender=sender_with_tokens.eth_address.hex(),
        contract=rw_lock_contract_containerized.eth_address.hex(),
        function_signature=function_signature,
        params=[acc_count],
    )
    account_list_for_execution_with_container = [
        rw_lock_contract_containerized.solana_address,
        sender_with_tokens.balance_account_address,
    ]
    assert set(emulate_accounts) == set(account_list_for_execution_with_container)

    operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
    evm_loader.send_transaction_step_from_instruction(
        operator_keypair,
        operator_balance,
        treasury_pool,
        holder_acc,
        signed_tx,
        account_list_for_execution_with_container,
        500,
        operator_keypair,
    )
    signed_tx2 = make_contract_call_trx(
        evm_loader, sender_with_tokens, rw_lock_contract_containerized, function_signature, [acc_count]
    )
    evm_loader.send_transaction_step_from_instruction(
        operator_keypair,
        operator_balance,
        treasury_pool,
        second_holder_acc,
        signed_tx2,
        account_list_for_execution_with_container,
        500,
        operator_keypair,
    )

    resp1 = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        holder_acc,
        signed_tx,
        account_list_for_execution_with_container,
    )
    resp2 = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair,
        treasury_pool,
        second_holder_acc,
        signed_tx2,
        account_list_for_execution_with_container,
    )
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp1, text="exit_status=0x11")
    check_transaction_logs_have_text(solana_client=evm_loader, trx=resp2, text="exit_status=0x11")


def test_cancel_trx_with_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    holder_acc,
    erc20_for_spl,
    sender_with_tokens,
    user_account,
    neon_rpc_client,
):
    function_signature = "transfer(address,uint256)"
    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=erc20_for_spl.solana_address,
        accounts=[erc20_for_spl.balance_account_address, user_account.balance_account_address],
    )
    additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender_with_tokens.eth_address.hex(),
        erc20_for_spl.eth_address.hex(),
        function_signature,
        [user_account.eth_address.hex(), 10],
    )
    signed_trx = make_contract_call_trx(
        evm_loader, sender_with_tokens, erc20_for_spl, function_signature, [user_account.eth_address.hex(), 10]
    )
    operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
    for _ in range(3):
        evm_loader.send_transaction_step_from_instruction(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            signed_trx,
            additional_accounts,
            500,
            operator_keypair,
        )

    evm_loader.send_cancel_transaction(operator_keypair, holder_acc, additional_accounts, signed_trx.hash)

    check_holder_account_tag(
        evm_loader,
        storage_account=holder_acc,
        layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
        expected_tag=TAG_FINALIZED_STATE,
    )


def test_resize_storage_sell_in_container(
    evm_loader,
    operator_keypair,
    treasury_pool,
    holder_acc,
    storage_checker_containerized,
    sender_with_tokens,
    neon_rpc_client,
):
    function_signature = "update_b(uint256)"
    additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
        sender_with_tokens.eth_address.hex(),
        storage_checker_containerized.eth_address.hex(),
        function_signature,
        [10],
    )
    signed_trx = make_contract_call_trx(
        evm_loader, sender_with_tokens, storage_checker_containerized, function_signature, [10]
    )
    evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_trx, additional_accounts
    )
    data_accounts = evm_loader.filter_neon_accounts_by_type(additional_accounts, AccountType.STORAGE)
    assert len(data_accounts) == 1, "There should be only one data account"

    evm_loader.assemble_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=storage_checker_containerized.solana_address,
        accounts=data_accounts + [storage_checker_containerized.balance_account_address],
    )
    container_size_before = len(evm_loader.get_solana_account_data(storage_checker_containerized.solana_address))
    function_signature = "update_c(uint256)"
    accounts_to_execute_trx_with_container = [
        storage_checker_containerized.solana_address,
        sender_with_tokens.balance_account_address,
    ]
    signed_trx = make_contract_call_trx(
        evm_loader, sender_with_tokens, storage_checker_containerized, function_signature, [20]
    )
    resp = evm_loader.execute_transaction_steps_from_instruction(
        operator_keypair, treasury_pool, holder_acc, signed_trx, accounts_to_execute_trx_with_container
    )
    check_transaction_logs_have_text(evm_loader, resp, "exit_status=0x11")
    container_size_after = len(evm_loader.get_solana_account_data(storage_checker_containerized.solana_address))
    assert container_size_after > container_size_before, "Container size did not increase after executing transaction"


def test_limits_of_container_allocation(
    evm_loader,
    operator_keypair,
    treasury_pool,
    rw_lock_contract_containerized,
):
    size = 1024 * 10
    evm_loader.allocate_container(
        operator=operator_keypair,
        treasury=treasury_pool,
        container_address=rw_lock_contract_containerized.solana_address,
        size=size,
    )
    size = size + 1
    with pytest.raises(AssertionError, match="Account data reallocation was invalid"):
        evm_loader.allocate_container(
            operator=operator_keypair,
            treasury=treasury_pool,
            container_address=rw_lock_contract_containerized.solana_address,
            size=size,
        )


def test_add_wrong_accounts_to_container(
    evm_loader, operator_keypair, treasury_pool, rw_lock_contract_containerized, sender_with_tokens, holder_acc
):
    not_suitable_accounts = [
        rw_lock_contract_containerized.solana_address,
        operator_keypair.pubkey(),
        sender_with_tokens.solana_account_address,
        holder_acc,
        treasury_pool.account,
        evm_loader.loader_id,
        Keypair().pubkey(),
    ]

    for account in not_suitable_accounts:
        with pytest.raises(AssertionError, match=r"not suitable for container|invalid owner"):
            evm_loader.assemble_container(
                operator=operator_keypair,
                treasury=treasury_pool,
                container_address=rw_lock_contract_containerized.solana_address,
                accounts=[account],
            )
