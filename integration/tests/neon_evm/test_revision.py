import pytest
import eth_abi
from solana.rpc.core import RPCException as SolanaRPCException
from solders.pubkey import Pubkey

from utils.evm_loader import EVM_STEPS
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from .utils.constants import TAG_FINALIZED_STATE, TAG_ACTIVE_STATE
from .utils.ethereum import make_contract_call_trx
from .utils.transaction_checks import (
    check_holder_account_tag,
    check_transaction_logs_have_text,
    check_transaction_logs_have_not_text,
)
from ..basic.helpers.assert_message import ErrorMessage


class TestAccountRevision:

    @pytest.fixture(scope="function")
    def revision_contract(
        self, request, evm_loader, operator_keypair, sender_with_tokens, neon_api_client, treasury_pool
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "common/Revision.sol",
            neon_api_client,
            treasury_pool,
            contract_name="RevisionChanger",
            version="0.8.12",
        )

    @pytest.fixture(scope="function")
    def revision_for_caller_contract(
        self, request, evm_loader, operator_keypair, sender_with_tokens, neon_api_client, treasury_pool
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "common/Revision.sol",
            neon_api_client,
            treasury_pool,
            contract_name="RevisionChangerForCaller",
            version="0.8.12",
        )

    @pytest.fixture(scope="function")
    def revision_contract_caller(
        self,
        request,
        revision_for_caller_contract,
        evm_loader,
        operator_keypair,
        sender_with_tokens,
        neon_api_client,
        treasury_pool,
    ):
        constructor_args = eth_abi.encode(["address"], [revision_for_caller_contract.eth_address.hex()])
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "common/Revision.sol",
            neon_api_client,
            treasury_pool,
            encoded_args=constructor_args,
            contract_name="RevisionChangerCaller",
            version="0.8.12",
        )

    @pytest.fixture(scope="class")
    def lender_contract(
        self, request, evm_loader, operator_keypair, sender_with_tokens, neon_api_client, treasury_pool
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "neon_evm/flash_loan/lender.sol",
            neon_api_client,
            treasury_pool,
            contract_name="LoanLender",
            version="0.8.12",
            value=100000,
        )

    @pytest.fixture(scope="class")
    def borrower_contract(
        self, request, evm_loader, operator_keypair, sender_with_tokens, neon_api_client, treasury_pool
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "neon_evm/flash_loan/borrower.sol",
            neon_api_client,
            treasury_pool,
            contract_name="LoanBorrower",
            version="0.8.12",
        )

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
            "update_storage_map_with_salt(uint256,uint256)",
            [data_storage_acc_count, 1],
        )
        acc_from_emulation = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        for i in range(trx_count):
            signed_tx = make_contract_call_trx(
                evm_loader,
                session_user,
                rw_lock_caller,
                "update_storage_map_with_salt(uint256,uint256)",
                [data_storage_acc_count, i + 1],
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
            if evm_loader.get_solana_balance(acc) > 0:
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
        sol_client,
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
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp1, text="exit_status=0x11")
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp2, text="exit_status=0x11")

        for holder in (holder1, holder2):
            check_holder_account_tag(
                solana_client=sol_client,
                storage_account=holder,
                layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
                expected_tag=TAG_FINALIZED_STATE,
            )

        contract_revision_after = evm_loader.get_contract_account_revision(rw_lock_contract.solana_address)
        assert contract_revision_before == contract_revision_after
        for acc in data_accounts1 + data_accounts2:
            if evm_loader.get_solana_balance(acc) > 0:
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
        sol_client,
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

        check_transaction_logs_have_text(solana_client=sol_client, trx=resp1, text="exit_status=0x11")

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
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp2, text="exit_status=0x11")

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
        sol_client,
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
        contract = evm_loader.deploy_contract(
            operator_keypair, session_user, "transfers", neon_api_client, treasury_pool
        )

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
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp1, text="exit_status=0x11")
        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder1,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

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
        sol_client,
    ):
        additional_accounts = [session_user.balance_account_address, rw_lock_contract.solana_address]
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        emulate_result = neon_api_client.emulate_contract_call(
            session_user.eth_address.hex(),
            rw_lock_contract.eth_address.hex(),
            "update_storage_map_with_salt(uint256,uint256)",
            [3, 1],
        )
        acc_from_emulation = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        data_accounts = set(acc_from_emulation) - set(additional_accounts)
        signed_tx1 = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "update_storage_map_with_salt(uint256,uint256)", [3, 1]
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

        for i in range(2):
            holder_acc_for_trx_from_instr = evm_loader.create_holder(operator_keypair)
            signed_tx2 = make_contract_call_trx(
                evm_loader, session_user, rw_lock_contract, "update_storage_map_with_salt(uint256,uint256)", [3, i + 1]
            )
            resp = evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc_for_trx_from_instr,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx2,
                acc_from_emulation,
            )
            check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x11")

        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            acc_from_emulation,
            EVM_STEPS,
            operator_keypair,
        )

        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x11")
        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

        for acc in data_accounts:
            if evm_loader.get_solana_balance(acc) > 0:
                data_acc_revision_after = evm_loader.get_data_account_revision(acc)
                assert data_acc_revision_after == 3

    def test_1_user_send_2_parallel_trx_with_neon_balance_change(
        self,
        operator_keypair,
        treasury_pool,
        neon_api_client,
        session_user,
        evm_loader,
        holder_acc,
        new_holder_acc,
    ):
        amount = 1000000
        evm_loader.deposit_neon(operator_keypair, session_user.eth_address, 4 * amount)
        sender_balance_before = evm_loader.get_neon_balance(session_user.eth_address)
        recipients = [evm_loader.make_new_user(operator_keypair), evm_loader.make_new_user(operator_keypair)]
        contract = evm_loader.deploy_contract(
            operator_keypair, session_user, "transfers", neon_api_client, treasury_pool
        )
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
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        evm_loader.send_transaction_step_from_account(
            operator_keypair, operator_balance_pubkey, treasury_pool, holder_acc, accounts, EVM_STEPS, operator_keypair
        )
        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_ACTIVE_STATE,
        )

        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair, operator_balance_pubkey, treasury_pool, holder_acc, accounts, EVM_STEPS, operator_keypair
        )  # the transaction was restarted
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
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
        holder_acc,
    ):
        sender = evm_loader.make_new_user(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        recipient = session_user

        evm_loader.deposit_neon(operator_keypair, sender.eth_address, 1000000)
        contract = evm_loader.deploy_contract(
            operator_keypair, session_user, "transfers", neon_api_client, treasury_pool
        )

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
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")
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
        holder_acc = evm_loader.create_holder(operator_keypair)
        contract = evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "transfers",
            neon_api_client,
            treasury_pool,
            value=1000,
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
        holder_acc_2 = evm_loader.create_holder(operator_keypair)
        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair, holder_acc_2, treasury_pool.account, treasury_pool.buffer, signed_tx2, accounts
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

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

        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")
        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

        assert evm_loader.get_neon_balance(contract.eth_address) == 900
        assert evm_loader.get_neon_balance(sender_with_tokens.eth_address) == sender_balance_before + 100

    @pytest.mark.parametrize(
        "func_signature, amount_emulated_accounts",
        [("powNumberInnerAndRollback(uint256)", 2), ("powNumberOuterAndRollback(uint256)", 3)],
    )
    def test_transaction_not_restarted_if_value_not_changed(
        self,
        revision_contract,
        operator_keypair,
        evm_loader,
        sender_with_tokens,
        neon_api_client,
        treasury_pool,
        new_holder_acc,
        new_holder_acc_2,
        func_signature,
        amount_emulated_accounts,
        second_session_user,
    ):
        func1_args = [15]
        emulate_result = neon_api_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(),
            revision_contract.eth_address.hex(),
            func_signature,
            func1_args,
        )
        emulated_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        assert len(emulated_accounts) == amount_emulated_accounts

        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, revision_contract, func_signature, func1_args
        )
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        evm_loader.write_transaction_to_holder_account(signed_tx, new_holder_acc, operator_keypair)

        # start first tx
        for i in range(1):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                new_holder_acc,
                emulated_accounts,
                EVM_STEPS,
                operator_keypair,
            )

        # make second transaction, change  number value and back original value in the same tx
        func2_args = [2]
        emulate_result2 = neon_api_client.emulate_contract_call(
            second_session_user.eth_address.hex(),
            revision_contract.eth_address.hex(),
            func_signature,
            func2_args,
        )
        emulated_accounts_2 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result2["solana_accounts"]]
        assert len(emulated_accounts) == amount_emulated_accounts

        signed_tx2 = make_contract_call_trx(
            evm_loader, second_session_user, revision_contract, func_signature, func2_args
        )
        evm_loader.write_transaction_to_holder_account(signed_tx2, new_holder_acc_2, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, new_holder_acc_2, emulated_accounts_2
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        # finish the first tx
        final_receipt = None
        for i in range(4):
            final_receipt = evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                new_holder_acc,
                emulated_accounts,
                EVM_STEPS,
                operator_keypair,
            )
            check_transaction_logs_have_not_text(solana_client=evm_loader, trx=final_receipt, text="INVALID_REVISION")
        check_transaction_logs_have_text(solana_client=evm_loader, trx=final_receipt, text="exit_status=0x11")

    def test_transaction_not_restarted_if_account_balance_value_not_changed(
        self,
        borrower_contract,
        lender_contract,
        operator_keypair,
        evm_loader,
        sender_with_tokens,
        neon_api_client,
        treasury_pool,
        new_holder_acc,
        new_holder_acc_2,
        second_session_user,
    ):

        # First tx prepare
        func_signature = "powAmount(uint256,uint256)"
        func1_args = [5, 10]

        emulate_result = neon_api_client.emulate_contract_call(
            second_session_user.eth_address.hex(), lender_contract.eth_address.hex(), func_signature, func1_args
        )

        emulated_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        signed_tx = make_contract_call_trx(evm_loader, second_session_user, lender_contract, func_signature, func1_args)

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        evm_loader.write_transaction_to_holder_account(signed_tx, new_holder_acc_2, operator_keypair)

        for i in range(2):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                new_holder_acc_2,
                emulated_accounts,
                EVM_STEPS,
                operator_keypair,
            )

        # second tx
        func2_signature = "flashLoan(address,uint256)"
        func2_args = [borrower_contract.eth_address, 9]

        emulate_result_2 = neon_api_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(), lender_contract.eth_address.hex(), func2_signature, func2_args, "0x9"
        )

        emulated_accounts_2 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result_2["solana_accounts"]]
        signed_tx2 = make_contract_call_trx(
            evm_loader, sender_with_tokens, lender_contract, func2_signature, func2_args, 9
        )

        evm_loader.write_transaction_to_holder_account(signed_tx2, new_holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, new_holder_acc, emulated_accounts_2
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")
        # finish first tx
        resp = None
        for i in range(3):
            resp = evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                new_holder_acc_2,
                emulated_accounts,
                EVM_STEPS,
                operator_keypair,
            )
            # check_transaction_logs_have_not_text(solana_client=evm_loader, trx=resp, text="INVALID_REVISION")
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x12")

    def test_balance_acc_revision_for_transaction_with_flash_loan(
        self,
        borrower_contract,
        lender_contract,
        operator_keypair,
        evm_loader,
        sender_with_tokens,
        neon_api_client,
        treasury_pool,
        new_holder_acc,
    ):

        balance_before = evm_loader.get_neon_balance(lender_contract.eth_address, evm_loader.chain_id)
        revision_before = evm_loader.get_balance_account_revision(lender_contract.balance_account_address)

        func_signature = "flashLoan(address,uint256)"
        func_args = [borrower_contract.eth_address, 9]

        emulate_result = neon_api_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(), lender_contract.eth_address.hex(), func_signature, func_args, "0x9"
        )

        emulated_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        signed_tx2 = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            lender_contract,
            func_signature,
            func_args,
        )

        evm_loader.write_transaction_to_holder_account(signed_tx2, new_holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, new_holder_acc, emulated_accounts
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        revision_after = evm_loader.get_balance_account_revision(lender_contract.balance_account_address)
        balance_after = evm_loader.get_neon_balance(lender_contract.eth_address, evm_loader.chain_id)

        assert balance_before == balance_after
        assert revision_before == revision_after

    def test_2_users_call_one_contract_with_nested_call(
        self,
        user_account,
        evm_loader,
        operator_keypair,
        treasury_pool,
        new_holder_acc,
        holder_acc,
        neon_api_client,
        revision_for_caller_contract,
        revision_contract_caller,
        session_user,
        sol_client,
    ):
        contract_revision_before = evm_loader.get_contract_account_revision(revision_for_caller_contract.solana_address)
        contract_revision_caller_before = evm_loader.get_contract_account_revision(
            revision_contract_caller.solana_address
        )
        user1 = session_user
        user2 = user_account
        holder1 = holder_acc
        holder2 = new_holder_acc
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        additional_accounts = [
            session_user.balance_account_address,
            revision_for_caller_contract.solana_address,
            revision_contract_caller.solana_address,
        ]

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
            user1.eth_address.hex(),
            revision_contract_caller.eth_address.hex(),
            "callRevisionChangerMethods(uint256)",
            [10],
        )

        acc_from_emulation1 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result1["solana_accounts"]]
        signed_tx1 = make_contract_call_trx(
            evm_loader,
            user1,
            revision_contract_caller,
            "callRevisionChangerMethods(uint256)",
            [10],
        )
        evm_loader.write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)

        emulate_result2 = neon_api_client.emulate_contract_call(
            user2.eth_address.hex(),
            revision_contract_caller.eth_address.hex(),
            "callRevisionChangerMethods(uint256)",
            [4],
        )

        acc_from_emulation2 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result2["solana_accounts"]]
        signed_tx2 = make_contract_call_trx(
            evm_loader,
            user2,
            revision_contract_caller,
            "callRevisionChangerMethods(uint256)",
            [4],
        )
        evm_loader.write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

        # we need 16 steps to complete trx1
        for _ in range(14):
            send_transaction_steps(holder1, acc_from_emulation1)

        resp2 = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder2, acc_from_emulation2
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp2, text="exit_status=0x11")

        resp1 = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder1, acc_from_emulation1
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp1, text="exit_status=0x11")

        contract_revision_after = evm_loader.get_contract_account_revision(revision_for_caller_contract.solana_address)
        contract_revision_caller_after = evm_loader.get_contract_account_revision(
            revision_contract_caller.solana_address
        )
        assert contract_revision_before == contract_revision_after - 2
        assert contract_revision_caller_before == contract_revision_caller_after

        data_accounts = set(acc_from_emulation1) - set(additional_accounts)
        for acc in data_accounts:
            data_acc_revision_after = evm_loader.get_data_account_revision(acc)
            assert data_acc_revision_after == 3
