import pytest
from solana.publickey import PublicKey

from integration.tests.neon_evm.solana_utils import execute_trx_from_instruction, write_transaction_to_holder_account, \
    execute_transaction_steps_from_account, EVM_STEPS, send_transaction_step_from_account, make_new_user, \
    deposit_neon
from integration.tests.neon_evm.utils.ethereum import make_eth_transaction
from .types.types import Caller
from .utils.constants import TAG_FINALIZED_STATE, TAG_ACTIVE_STATE
from .utils.contract import make_contract_call_trx, deploy_contract

from .utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from .utils.transaction_checks import check_holder_account_tag, check_transaction_logs_have_text


class TestAccountRevision:

    def test_several_simple_trx(self, operator_keypair, treasury_pool,
                                sender_with_tokens: Caller, session_user: Caller,
                                evm_loader):
        trx_count = 6
        sender_revisions_before = evm_loader.get_balance_account_revision(sender_with_tokens.balance_account_address)
        recipient_revisions_before = evm_loader.get_balance_account_revision(session_user.balance_account_address)
        for i in range(trx_count):
            signed_tx = make_eth_transaction(session_user.eth_address, None, sender_with_tokens, 10)
            execute_trx_from_instruction(operator_keypair, evm_loader, treasury_pool.account, treasury_pool.buffer,
                                         signed_tx,
                                         [sender_with_tokens.balance_account_address,
                                          session_user.balance_account_address,
                                          session_user.solana_account_address],
                                         operator_keypair)

        sender_revisions_after = evm_loader.get_balance_account_revision(sender_with_tokens.balance_account_address)
        recipient_revisions_after = evm_loader.get_balance_account_revision(session_user.balance_account_address)
        assert sender_revisions_after == sender_revisions_before + trx_count
        assert recipient_revisions_after == recipient_revisions_before + trx_count

    def test_call_contract_with_changing_data(self, operator_keypair, treasury_pool, rw_lock_caller, rw_lock_contract,
                                              session_user,
                                              evm_loader, holder_acc, neon_api_client):
        trx_count = 5
        data_storage_acc_count = 3
        sender_revisions_before = evm_loader.get_balance_account_revision(session_user.balance_account_address)
        contract_revisions_before = evm_loader.get_contract_account_revision(rw_lock_contract.solana_address)
        contract2_revisions_before = evm_loader.get_contract_account_revision(rw_lock_caller.solana_address)
        additional_accounts = [session_user.balance_account_address,
                               rw_lock_contract.solana_address,
                               rw_lock_caller.solana_address]
        emulate_result = neon_api_client.emulate_contract_call(session_user.eth_address.hex(),
                                                               rw_lock_caller.eth_address.hex(),
                                                               'update_storage_map(uint256)', [data_storage_acc_count])
        acc_from_emulation = [PublicKey(item['pubkey']) for item in emulate_result['solana_accounts']]

        for i in range(trx_count):
            signed_tx = make_contract_call_trx(session_user, rw_lock_caller, 'update_storage_map(uint256)',
                                               [data_storage_acc_count])
            write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            execute_transaction_steps_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                                   acc_from_emulation)
        sender_revisions_after = evm_loader.get_balance_account_revision(session_user.balance_account_address)
        contract_revisions_after = evm_loader.get_contract_account_revision(rw_lock_contract.solana_address)
        contract2_revisions_after = evm_loader.get_contract_account_revision(rw_lock_caller.solana_address)
        assert sender_revisions_before == sender_revisions_after
        assert contract_revisions_before == contract_revisions_after
        assert contract2_revisions_before == contract2_revisions_after

        data_accounts = set(acc_from_emulation) - set(additional_accounts)
        assert len(data_accounts) == data_storage_acc_count
        for acc in data_accounts:
            data_acc_revisions_after = evm_loader.get_contract_account_revision(acc)
            assert data_acc_revisions_after == trx_count

    def test_2_users_call_one_contract_with_different_storage_accounts(self, rw_lock_contract, user_account,
                                                                       evm_loader, operator_keypair,
                                                                       treasury_pool, new_holder_acc, holder_acc,
                                                                       neon_api_client, session_user):
        data_storage_acc_count = 4
        user1 = session_user
        user2 = user_account
        holder1 = holder_acc
        holder2 = new_holder_acc
        user1_revisions_before = evm_loader.get_balance_account_revision(user1.balance_account_address)
        user2_revisions_before = evm_loader.get_balance_account_revision(user2.balance_account_address)
        signed_tx1 = make_contract_call_trx(user1, rw_lock_contract, 'update_storage_map(uint256)',
                                            [data_storage_acc_count])
        write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)

        emulate_result1 = neon_api_client.emulate_contract_call(user1.eth_address.hex(),
                                                                rw_lock_contract.eth_address.hex(),
                                                                'update_storage_map(uint256)', [data_storage_acc_count])
        acc_from_emulation1 = [PublicKey(item['pubkey']) for item in emulate_result1['solana_accounts']]

        signed_tx2 = make_contract_call_trx(user2, rw_lock_contract, 'update_storage_map(uint256)',
                                            [data_storage_acc_count])

        emulate_result2 = neon_api_client.emulate_contract_call(user2.eth_address.hex(),
                                                                rw_lock_contract.eth_address.hex(),
                                                                'update_storage_map(uint256)', [data_storage_acc_count])
        acc_from_emulation2 = [PublicKey(item['pubkey']) for item in emulate_result2['solana_accounts']]

        write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

        def send_transaction_steps(holder_account, accounts):
            return send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_account,
                                                      accounts, EVM_STEPS, operator_keypair)

        send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)
        send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)
        resp1 = send_transaction_steps(holder1, acc_from_emulation1)
        resp2 = send_transaction_steps(holder2, acc_from_emulation2)
        check_transaction_logs_have_text(resp1.value.transaction.transaction.signatures[0], "exit_status=0x11")
        check_transaction_logs_have_text(resp2.value.transaction.transaction.signatures[0], "exit_status=0x11")

        check_holder_account_tag(holder1, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_holder_account_tag(holder2, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        user1_revision_after = evm_loader.get_balance_account_revision(user1.balance_account_address)
        user2_revision_after = evm_loader.get_balance_account_revision(user2.balance_account_address)
        assert user1_revisions_before == user1_revision_after
        assert user2_revisions_before == user2_revision_after

    # TODO: add case (4, 0) after fixing NDEV-2698
    @pytest.mark.parametrize("storage_data_len, expected_count_data_acc", [(60, 1)])
    def test_2_users_call_one_contract_with_the_same_storages(self, user_account,
                                                              evm_loader, operator_keypair,
                                                              treasury_pool, new_holder_acc, holder_acc,
                                                              neon_api_client, rw_lock_contract,
                                                              session_user, storage_data_len, expected_count_data_acc):
        user1 = session_user
        user2 = user_account
        holder1 = holder_acc
        holder2 = new_holder_acc
        text1 = "a" * storage_data_len
        text2 = "b" * storage_data_len

        def send_transaction_steps(holder_account, accounts):
            return send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_account,
                                                      accounts, EVM_STEPS, operator_keypair)

        emulate_result1 = neon_api_client.emulate_contract_call(user1.eth_address.hex(),
                                                                rw_lock_contract.eth_address.hex(),
                                                                'update_storage_str(string)', [text1])

        acc_from_emulation1 = [PublicKey(item['pubkey']) for item in emulate_result1['solana_accounts']]
        signed_tx1 = make_contract_call_trx(user1, rw_lock_contract, 'update_storage_str(string)', [text1])

        write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)

        emulate_result2 = neon_api_client.emulate_contract_call(user2.eth_address.hex(),
                                                                rw_lock_contract.eth_address.hex(),
                                                                'update_storage_str(string)', [text2])
        acc_from_emulation2 = [PublicKey(item['pubkey']) for item in emulate_result2['solana_accounts']]
        signed_tx2 = make_contract_call_trx(user2, rw_lock_contract, 'update_storage_str(string)', [text2])
        write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

        send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)
        send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)
        resp1 = send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)

        check_transaction_logs_have_text(resp1.value.transaction.transaction.signatures[0], "exit_status=0x11")

        if expected_count_data_acc > 0:
            additional_accounts = [user1.balance_account_address,
                                   rw_lock_contract.solana_address,
                                   rw_lock_contract.balance_account_address]
            data_account = list(set(acc_from_emulation1) - set(additional_accounts))[0]
            data_acc_revisions_after_user1_finished = evm_loader.get_contract_account_revision(data_account)
            assert data_acc_revisions_after_user1_finished == 1

        # repeat steps for second user because revision for data accounts is changed
        resp2 = send_transaction_steps(holder2, acc_from_emulation2)
        check_transaction_logs_have_text(resp2.value.transaction.transaction.signatures[0], "exit_status=0x11")

        if expected_count_data_acc > 0:
            data_acc_revisions_after_user2_finished = evm_loader.get_contract_account_revision(data_account)
            assert data_acc_revisions_after_user2_finished == 2


def test_2_users_sent_neons_to_the_same_recipients(operator_keypair, treasury_pool, neon_api_client, session_user,
                                                   user_account, evm_loader, holder_acc, new_holder_acc):
    sender1 = session_user
    sender2 = user_account
    holder1 = holder_acc
    holder2 = new_holder_acc
    amount = 1000000
    deposit_neon(evm_loader, operator_keypair, sender1.eth_address, 3 * amount)
    deposit_neon(evm_loader, operator_keypair, sender2.eth_address, 3 * amount)
    recipients = [make_new_user(evm_loader), make_new_user(evm_loader), make_new_user(evm_loader)]
    contract = deploy_contract(operator_keypair, session_user, "transfers", evm_loader, treasury_pool)

    recipients_eth_addresses = [rec.eth_address for rec in recipients]
    signed_tx1 = make_contract_call_trx(sender1, contract, 'transferNeon(uint256,address[])',
                                        [amount, recipients_eth_addresses],
                                        value=3 * amount)
    write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)
    signed_tx2 = make_contract_call_trx(sender2, contract, 'transferNeon(uint256,address[])',
                                        [amount, recipients_eth_addresses],
                                        value=3 * amount)
    write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

    def send_transaction_steps(holder_account, sender):
        accounts = [rec.balance_account_address for rec in recipients] + \
                   [rec.solana_account_address for rec in recipients]
        accounts += [sender.balance_account_address,
                     sender.solana_account_address,
                     contract.balance_account_address,
                     contract.solana_address]
        return send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_account,
                                                  accounts, EVM_STEPS, operator_keypair)

    send_transaction_steps(holder1, sender1)
    send_transaction_steps(holder2, sender2)
    send_transaction_steps(holder1, sender1)
    send_transaction_steps(holder2, sender2)
    resp1 = send_transaction_steps(holder1, sender1)
    send_transaction_steps(holder2, sender2)
    check_transaction_logs_have_text(resp1.value.transaction.transaction.signatures[0], "exit_status=0x11")
    check_holder_account_tag(holder1, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
    check_holder_account_tag(holder2, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_ACTIVE_STATE)

    # repeat steps for second user because revision for data accounts is changed
    resp2 = send_transaction_steps(holder2, sender2)
    check_transaction_logs_have_text(resp2.value.transaction.transaction.signatures[0], "exit_status=0x11")
    check_holder_account_tag(holder2, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
    for acc in recipients:
        assert evm_loader.get_balance_account_revision(acc.balance_account_address) == 2
        assert evm_loader.get_neon_balance(acc.eth_address) == amount * 2


def test_1_user_2_parallel_trx_with_data_change(operator_keypair, treasury_pool, neon_api_client, session_user,
                                                rw_lock_contract,
                                                user_account, evm_loader, holder_acc, new_holder_acc):
    additional_accounts = [session_user.balance_account_address,
                           rw_lock_contract.solana_address]
    emulate_result = neon_api_client.emulate_contract_call(session_user.eth_address.hex(),
                                                           rw_lock_contract.eth_address.hex(),
                                                           'update_storage_map(uint256)', [3])
    acc_from_emulation = [PublicKey(item['pubkey']) for item in emulate_result['solana_accounts']]
    data_accounts = set(acc_from_emulation) - set(additional_accounts)
    signed_tx1 = make_contract_call_trx(session_user, rw_lock_contract, 'update_storage_map(uint256)', [3])
    write_transaction_to_holder_account(signed_tx1, holder_acc, operator_keypair)

    send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                       acc_from_emulation, EVM_STEPS, operator_keypair)
    send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                       acc_from_emulation, EVM_STEPS, operator_keypair)

    for _ in range(2):
        signed_tx2 = make_contract_call_trx(session_user, rw_lock_contract, 'update_storage_map(uint256)', [3])
        resp = execute_trx_from_instruction(operator_keypair, evm_loader, treasury_pool.account, treasury_pool.buffer,
                                            signed_tx2,
                                            acc_from_emulation,
                                            operator_keypair)
        check_transaction_logs_have_text(resp.value, "exit_status=0x11")

    send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                       acc_from_emulation, EVM_STEPS, operator_keypair)
    resp = send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                              acc_from_emulation, EVM_STEPS, operator_keypair)
    check_transaction_logs_have_text(resp.value.transaction.transaction.signatures[0], "exit_status=0x11")
    check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
    for acc in data_accounts:
        data_acc_revisions_after = evm_loader.get_contract_account_revision(acc)
        assert data_acc_revisions_after == 3


def test_1_user_send_2_parallel_trx_with_neon_balance_change(operator_keypair, treasury_pool, neon_api_client,
                                                             session_user, rw_lock_contract,
                                                             user_account, evm_loader, holder_acc, new_holder_acc):
    amount = 1000000
    deposit_neon(evm_loader, operator_keypair, session_user.eth_address, 3 * amount)
    recipients = [make_new_user(evm_loader), make_new_user(evm_loader)]
    contract = deploy_contract(operator_keypair, session_user, "transfers", evm_loader, treasury_pool)

    sender_revisions_before = evm_loader.get_balance_account_revision(session_user.balance_account_address)
    recipients_eth_addresses = [rec.eth_address for rec in recipients]
    signed_tx1 = make_contract_call_trx(session_user, contract, 'transferNeon(uint256,address[])',
                                        [amount, recipients_eth_addresses],
                                        value=3 * amount)
    accounts = [rec.balance_account_address for rec in recipients] + \
               [rec.solana_account_address for rec in recipients]
    accounts += [session_user.balance_account_address,
                 session_user.solana_account_address,
                 contract.balance_account_address,
                 contract.solana_address]

    write_transaction_to_holder_account(signed_tx1, holder_acc, operator_keypair)
    send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                       accounts, EVM_STEPS, operator_keypair)
    send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                       accounts, EVM_STEPS, operator_keypair)

    signed_tx2 = make_contract_call_trx(session_user, contract, 'transferNeon(uint256,address[])',
                                        [amount, recipients_eth_addresses],
                                        value=3 * amount)

    resp = execute_trx_from_instruction(operator_keypair, evm_loader, treasury_pool.account, treasury_pool.buffer,
                                        signed_tx2,
                                        accounts,
                                        operator_keypair)
    check_transaction_logs_have_text(resp.value, "exit_status=0x11")

    send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                       accounts, EVM_STEPS, operator_keypair)
    resp = send_transaction_step_from_account(operator_keypair, evm_loader, treasury_pool, holder_acc,
                                              accounts, EVM_STEPS, operator_keypair)
    check_transaction_logs_have_text(resp.value.transaction.transaction.signatures[0], "exit_status=0x11")
    check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
    sender_revisions_after = evm_loader.get_balance_account_revision(session_user.balance_account_address)
    assert sender_revisions_before == sender_revisions_after - 2
