import pytest
from solana.rpc.core import RPCException as SolanaRPCException
from solders.pubkey import Pubkey

from utils.evm_loader import EVM_STEPS
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT

from .utils.constants import TAG_FINALIZED_STATE, TAG_ACTIVE_STATE
from .utils.contract import make_contract_call_trx, deploy_contract


from .utils.storage import create_holder

from .utils.transaction_checks import check_holder_account_tag, check_transaction_logs_have_text
from ..basic.helpers.assert_message import ErrorMessage


class TestAccountRevision:
    def test_call_contract_with_changing_data(
        self,
        operator_keypair,
        holder_acc,
        treasury_pool,
        rw_lock_caller,
        rw_lock_contract,
        session_user,
        evm_loader,
        neon_api_client,
    ):
        trx_count = 4
        data_storage_acc_count = 3
        contract_revision_before = evm_loader.get_contract_account_revision(rw_lock_contract.solana_address)
        contract2_revision_before = evm_loader.get_contract_account_revision(rw_lock_caller.solana_address)
        additional_accounts = [
            session_user.balance_account_address,
            rw_lock_contract.solana_address,
            rw_lock_caller.solana_address,
        ]
        emulate_result = neon_api_client.emulate_contract_call(
            session_user.eth_address.hex(),
            rw_lock_caller.eth_address.hex(),
            "update_storage_map(uint256)",
            [data_storage_acc_count],
        )
        acc_from_emulation = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        for i in range(trx_count):
            signed_tx = make_contract_call_trx(
                evm_loader, session_user, rw_lock_caller, "update_storage_map(uint256)", [data_storage_acc_count]
            )
            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, acc_from_emulation
            )
        contract_revision_after = evm_loader.get_contract_account_revision(rw_lock_contract.solana_address)
        contract2_revision_after = evm_loader.get_contract_account_revision(rw_lock_caller.solana_address)
        assert contract_revision_before == contract_revision_after
        assert contract2_revision_before == contract2_revision_after

        data_accounts = set(acc_from_emulation) - set(additional_accounts)
        assert len(data_accounts) == data_storage_acc_count
        for acc in data_accounts:
            data_acc_revision_after = evm_loader.get_data_account_revision(acc)
            assert data_acc_revision_after == trx_count

    def test_2_users_call_one_contract_with_different_storage_accounts(
        self,
        rw_lock_contract,
        user_account,
        evm_loader,
        operator_keypair,
        treasury_pool,
        new_holder_acc,
        holder_acc,
        neon_api_client,
        session_user,
    ):
        data_storage_acc_count = 4
        user1 = session_user
        user2 = user_account
        holder1 = holder_acc
        holder2 = new_holder_acc
        signed_tx1 = make_contract_call_trx(
            evm_loader, user1, rw_lock_contract, "update_storage_map(uint256)", [data_storage_acc_count]
        )
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        def send_transaction_steps(holder_account, accounts):
            return evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder_account,
                accounts,
                EVM_STEPS,
                operator_keypair,
            )

        evm_loader.write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)
        contract_revision_before = evm_loader.get_contract_account_revision(rw_lock_contract.solana_address)
        emulate_result1 = neon_api_client.emulate_contract_call(
            user1.eth_address.hex(),
            rw_lock_contract.eth_address.hex(),
            "update_storage_map(uint256)",
            [data_storage_acc_count],
        )
        acc_from_emulation1 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result1["solana_accounts"]]
        data_accounts1 = list(
            set(acc_from_emulation1) - {user1.balance_account_address, rw_lock_contract.solana_address}
        )
        signed_tx2 = make_contract_call_trx(
            evm_loader, user2, rw_lock_contract, "update_storage_map(uint256)", [data_storage_acc_count]
        )

        emulate_result2 = neon_api_client.emulate_contract_call(
            user2.eth_address.hex(),
            rw_lock_contract.eth_address.hex(),
            "update_storage_map(uint256)",
            [data_storage_acc_count],
        )
        acc_from_emulation2 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result2["solana_accounts"]]
        data_accounts2 = list(
            set(acc_from_emulation2) - {user2.balance_account_address, rw_lock_contract.solana_address}
        )
        evm_loader.write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

        send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)
        send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)
        resp1 = send_transaction_steps(holder1, acc_from_emulation1)
        resp2 = send_transaction_steps(holder2, acc_from_emulation2)
        check_transaction_logs_have_text(resp1, "exit_status=0x11")
        check_transaction_logs_have_text(resp2, "exit_status=0x11")

        check_holder_account_tag(holder1, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_holder_account_tag(holder2, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        contract_revision_after = evm_loader.get_contract_account_revision(rw_lock_contract.solana_address)
        assert contract_revision_before == contract_revision_after
        for acc in data_accounts1 + data_accounts2:
            data_acc_revision = evm_loader.get_data_account_revision(acc)
            assert data_acc_revision == 1

    # TODO: add case (4, 0) after fixing NDEV-2698
    @pytest.mark.parametrize("storage_data_len, expected_count_data_acc", [(60, 1)])
    def test_2_users_call_one_contract_with_the_same_storages(
        self,
        user_account,
        evm_loader,
        operator_keypair,
        treasury_pool,
        new_holder_acc,
        holder_acc,
        neon_api_client,
        rw_lock_contract,
        session_user,
        storage_data_len,
        expected_count_data_acc,
    ):
        user1 = session_user
        user2 = user_account
        holder1 = holder_acc
        holder2 = new_holder_acc
        text1 = "a" * storage_data_len
        text2 = "b" * storage_data_len
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        def send_transaction_steps(holder_account, accounts):
            return evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder_account,
                accounts,
                EVM_STEPS,
                operator_keypair,
            )

        emulate_result1 = neon_api_client.emulate_contract_call(
            user1.eth_address.hex(), rw_lock_contract.eth_address.hex(), "update_storage_str(string)", [text1]
        )

        acc_from_emulation1 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result1["solana_accounts"]]
        signed_tx1 = make_contract_call_trx(evm_loader, user1, rw_lock_contract, "update_storage_str(string)", [text1])

        evm_loader.write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)

        emulate_result2 = neon_api_client.emulate_contract_call(
            user2.eth_address.hex(), rw_lock_contract.eth_address.hex(), "update_storage_str(string)", [text2]
        )
        acc_from_emulation2 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result2["solana_accounts"]]
        signed_tx2 = make_contract_call_trx(evm_loader, user2, rw_lock_contract, "update_storage_str(string)", [text2])
        evm_loader.write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

        send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)
        send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)
        resp1 = send_transaction_steps(holder1, acc_from_emulation1)
        send_transaction_steps(holder2, acc_from_emulation2)

        check_transaction_logs_have_text(resp1, "exit_status=0x11")

        if expected_count_data_acc > 0:
            additional_accounts = [
                user1.balance_account_address,
                rw_lock_contract.solana_address,
                rw_lock_contract.balance_account_address,
            ]
            data_account = list(set(acc_from_emulation1) - set(additional_accounts))[0]
            data_acc_revision_after_user1_finished = evm_loader.get_data_account_revision(data_account)
            assert data_acc_revision_after_user1_finished == 1

        # repeat steps for second user because revision for data accounts is changed
        resp2 = send_transaction_steps(holder2, acc_from_emulation2)
        check_transaction_logs_have_text(resp2, "exit_status=0x11")

        if expected_count_data_acc > 0:
            data_acc_revision_after_user2_finished = evm_loader.get_data_account_revision(data_account)
            assert data_acc_revision_after_user2_finished == 2

    def test_2_users_sent_neons_to_the_same_recipients(
        self,
        operator_keypair,
        treasury_pool,
        neon_api_client,
        session_user,
        user_account,
        evm_loader,
        holder_acc,
        new_holder_acc,
    ):
        sender1 = session_user
        sender2 = user_account
        holder1 = holder_acc
        holder2 = new_holder_acc
        amount = 1000000
        evm_loader.deposit_neon(operator_keypair, sender1.eth_address, 3 * amount)
        evm_loader.deposit_neon(operator_keypair, sender2.eth_address, 3 * amount)
        recipients = [
            evm_loader.make_new_user(operator_keypair),
            evm_loader.make_new_user(operator_keypair),
            evm_loader.make_new_user(operator_keypair),
        ]
        contract = deploy_contract(operator_keypair, session_user, "transfers", evm_loader, treasury_pool)

        recipients_eth_addresses = [rec.eth_address for rec in recipients]
        signed_tx1 = make_contract_call_trx(
            evm_loader,
            sender1,
            contract,
            "transferNeon(uint256,address[])",
            [amount, recipients_eth_addresses],
            value=3 * amount,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)
        signed_tx2 = make_contract_call_trx(
            evm_loader,
            sender2,
            contract,
            "transferNeon(uint256,address[])",
            [amount, recipients_eth_addresses],
            value=3 * amount,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

        def send_transaction_steps(holder_account, sender):
            accounts = [rec.balance_account_address for rec in recipients] + [
                rec.solana_account_address for rec in recipients
            ]
            accounts += [
                sender.balance_account_address,
                sender.solana_account_address,
                contract.balance_account_address,
                contract.solana_address,
            ]
            operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
            return evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder_account,
                accounts,
                EVM_STEPS,
                operator_keypair,
            )

        send_transaction_steps(holder1, sender1)
        send_transaction_steps(holder2, sender2)
        send_transaction_steps(holder1, sender1)
        send_transaction_steps(holder2, sender2)
        resp1 = send_transaction_steps(holder1, sender1)

        send_transaction_steps(holder2, sender2)
        check_transaction_logs_have_text(resp1, "exit_status=0x11")
        check_holder_account_tag(holder1, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)

        resp2 = send_transaction_steps(holder2, sender2)  # the transaction was restarted
        check_holder_account_tag(holder2, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_transaction_logs_have_text(resp2, "exit_status=0x11")

        check_holder_account_tag(holder2, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        for acc in recipients:
            assert evm_loader.get_neon_balance(acc.eth_address) == amount * 2

    def test_1_user_2_parallel_trx_with_data_change(
        self,
        operator_keypair,
        treasury_pool,
        neon_api_client,
        session_user,
        rw_lock_contract,
        user_account,
        evm_loader,
        holder_acc,
        new_holder_acc,
    ):
        additional_accounts = [session_user.balance_account_address, rw_lock_contract.solana_address]
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        emulate_result = neon_api_client.emulate_contract_call(
            session_user.eth_address.hex(), rw_lock_contract.eth_address.hex(), "update_storage_map(uint256)", [3]
        )
        acc_from_emulation = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        data_accounts = set(acc_from_emulation) - set(additional_accounts)
        signed_tx1 = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "update_storage_map(uint256)", [3]
        )
        evm_loader.write_transaction_to_holder_account(signed_tx1, holder_acc, operator_keypair)

        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            acc_from_emulation,
            EVM_STEPS,
            operator_keypair,
        )
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            acc_from_emulation,
            EVM_STEPS,
            operator_keypair,
        )

        for _ in range(2):
            holder_acc_for_trx_from_instr = create_holder(operator_keypair, evm_loader)
            signed_tx2 = make_contract_call_trx(evm_loader, session_user, rw_lock_contract, "update_storage_map(uint256)", [3])
            resp = evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc_for_trx_from_instr,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx2,
                acc_from_emulation
            )
            check_transaction_logs_have_text(resp, "exit_status=0x11")
        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            acc_from_emulation,
            EVM_STEPS,
            operator_keypair,
        )

        check_transaction_logs_have_text(resp, "exit_status=0x11")
        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        for acc in data_accounts:
            data_acc_revision_after = evm_loader.get_data_account_revision(acc)
            assert data_acc_revision_after == 3

    def test_1_user_send_2_parallel_trx_with_neon_balance_change(
        self, operator_keypair, treasury_pool, neon_api_client, session_user, evm_loader, holder_acc, new_holder_acc
    ):
        amount = 1000000
        evm_loader.deposit_neon(operator_keypair, session_user.eth_address, 4 * amount)
        sender_balance_before = evm_loader.get_neon_balance(session_user.eth_address)
        recipients = [evm_loader.make_new_user(operator_keypair), evm_loader.make_new_user(operator_keypair)]
        contract = deploy_contract(operator_keypair, session_user, "transfers", evm_loader, treasury_pool)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        recipients_eth_addresses = [rec.eth_address for rec in recipients]
        signed_tx1 = make_contract_call_trx(
            evm_loader,
            session_user,
            contract,
            "transferNeon(uint256,address[])",
            [amount, recipients_eth_addresses],
            value=amount * 2,
        )
        accounts = [rec.balance_account_address for rec in recipients] + [
            rec.solana_account_address for rec in recipients
        ]
        accounts += [
            session_user.balance_account_address,
            session_user.solana_account_address,
            contract.balance_account_address,
            contract.solana_address,
        ]

        evm_loader.write_transaction_to_holder_account(signed_tx1, holder_acc, operator_keypair)
        evm_loader.send_transaction_step_from_account(
            operator_keypair, operator_balance_pubkey, treasury_pool, holder_acc, accounts, EVM_STEPS, operator_keypair
        )
        evm_loader.send_transaction_step_from_account(
            operator_keypair, operator_balance_pubkey, treasury_pool, holder_acc, accounts, EVM_STEPS, operator_keypair
        )

        signed_tx2 = make_contract_call_trx(
            evm_loader,
            session_user,
            contract,
            "transferNeon(uint256,address[])",
            [amount, recipients_eth_addresses],
            value=amount * 2,
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair, new_holder_acc, treasury_pool.account, treasury_pool.buffer, signed_tx2, accounts
        )
        check_transaction_logs_have_text(resp, "exit_status=0x11")

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        evm_loader.send_transaction_step_from_account(
            operator_keypair, operator_balance_pubkey, treasury_pool, holder_acc, accounts, EVM_STEPS, operator_keypair
        )
        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_ACTIVE_STATE)

        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair, operator_balance_pubkey, treasury_pool, holder_acc, accounts, EVM_STEPS, operator_keypair
        )  # the transaction was restarted
        check_transaction_logs_have_text(resp, "exit_status=0x11")

        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        for acc in recipients:
            assert evm_loader.get_neon_balance(acc.eth_address) == amount * 2
        assert evm_loader.get_neon_balance(session_user.eth_address) == sender_balance_before - 4 * amount

    def test_insufficient_balance_for_2_parallel_trx(
        self,
        operator_keypair,
        treasury_pool,
        neon_api_client,
        session_user,
        evm_loader,
        new_holder_acc,
        holder_acc
    ):
        sender = evm_loader.make_new_user(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        recipient = session_user

        evm_loader.deposit_neon(operator_keypair, sender.eth_address, 1000000)
        contract = deploy_contract(operator_keypair, session_user, "transfers", evm_loader, treasury_pool)

        amount = evm_loader.get_neon_balance(sender.eth_address)

        signed_tx1 = make_contract_call_trx(
            evm_loader,
            sender,
            contract,
            "transferNeon(uint256,address[])",
            [amount // 2, [recipient.eth_address]],
            value=amount // 2,
        )
        accounts = [
            sender.balance_account_address,
            sender.solana_account_address,
            contract.balance_account_address,
            contract.solana_address,
            recipient.balance_account_address,
            recipient.solana_account_address,
        ]

        evm_loader.write_transaction_to_holder_account(signed_tx1, new_holder_acc, operator_keypair)
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            new_holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            new_holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )

        signed_tx2 = make_contract_call_trx(
            evm_loader,
            sender,
            contract,
            "transferNeon(uint256,address[])",
            [amount, [recipient.eth_address]],
            value=amount,
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair, holder_acc, treasury_pool.account, treasury_pool.buffer, signed_tx2, accounts
        )
        check_transaction_logs_have_text(resp, "exit_status=0x11")
        with pytest.raises(SolanaRPCException, match=ErrorMessage.INSUFFICIENT_BALANCE.value):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                new_holder_acc,
                accounts,
                EVM_STEPS,
                operator_keypair,
            )

    def test_parallel_change_balance_in_one_trx_and_check_in_second_trx(
        self, operator_keypair, treasury_pool, neon_api_client, sender_with_tokens, evm_loader
    ):
        holder_acc = create_holder(operator_keypair, evm_loader)
        contract = deploy_contract(
            operator_keypair, sender_with_tokens, "transfers", evm_loader, treasury_pool, value=1000
        )
        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)

        signed_tx1 = make_contract_call_trx(evm_loader, sender_with_tokens, contract, "donateTenPercent()")
        accounts = [
            sender_with_tokens.balance_account_address,
            sender_with_tokens.solana_account_address,
            contract.balance_account_address,
            contract.solana_address,
        ]

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        evm_loader.write_transaction_to_holder_account(signed_tx1, holder_acc, operator_keypair)
        evm_loader.send_transaction_step_from_account(
            operator_keypair, operator_balance_pubkey, treasury_pool, holder_acc, accounts, EVM_STEPS, operator_keypair
        )
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )

        signed_tx2 = make_contract_call_trx(evm_loader, sender_with_tokens, contract, "donateTenPercent()")
        holder_acc_2 = create_holder(operator_keypair, evm_loader)
        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc_2,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx2,
            accounts
        )
        check_transaction_logs_have_text(resp, "exit_status=0x11")

        for _ in range(2):
            resp = evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder_acc,
                accounts,
                EVM_STEPS,
                operator_keypair,
            )

        check_transaction_logs_have_text(resp, "exit_status=0x11")
        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)

        assert evm_loader.get_neon_balance(contract.eth_address) == 900
        assert evm_loader.get_neon_balance(sender_with_tokens.eth_address) == sender_balance_before + 100
