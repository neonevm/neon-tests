import pytest
import eth_abi

from solana.rpc.core import RPCException as SolanaRPCException
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from utils.evm_loader import EVM_STEPS
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from utils.metaplex import ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID
from utils.instructions import make_create_associated_token_idempotent
from utils.helpers import bytes32_to_solana_pubkey, serialize_instruction
from .utils.constants import TAG_FINALIZED_STATE, TAG_ACTIVE_STATE
from .utils.ethereum import make_contract_call_trx
from .utils.transaction_checks import (
    check_holder_account_tag,
    check_transaction_logs_have_text,
    check_transaction_logs_have_not_text,
)
from ..basic.helpers.assert_message import ErrorMessage


class TestAccountRevision:
    @pytest.fixture(scope="session")
    def revision_contract(
        self, request, evm_loader, operator_keypair, sender_with_tokens, neon_rpc_client, treasury_pool
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "common/Revision.sol",
            neon_rpc_client,
            treasury_pool,
            contract_name="RevisionChanger",
            version="0.8.12",
        )

    @pytest.fixture(scope="session")
    def revision_contract_caller(
        self,
        request,
        revision_contract,
        evm_loader,
        operator_keypair,
        sender_with_tokens,
        neon_rpc_client,
        treasury_pool,
    ):
        constructor_args = eth_abi.encode(["address"], [revision_contract.eth_address.hex()])
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "common/Revision.sol",
            neon_rpc_client,
            treasury_pool,
            encoded_args=constructor_args,
            contract_name="RevisionChangerCaller",
            version="0.8.12",
        )

    @pytest.fixture(scope="session")
    def revision_with_solana_call_contract(
        self,
        request,
        evm_loader,
        operator_keypair,
        sender_with_tokens,
        neon_rpc_client,
        treasury_pool,
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "common/RevisionWithSolanaCall.sol",
            neon_rpc_client,
            treasury_pool,
            contract_name="RevisionChangerWithSolanaCall",
            version="0.8.28",
        )

    @pytest.fixture(scope="session")
    def lender_contract(
        self, request, evm_loader, operator_keypair, sender_with_tokens, neon_rpc_client, treasury_pool
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "neon_evm/flash_loan/lender.sol",
            neon_rpc_client,
            treasury_pool,
            value=100000,
            contract_name="LoanLender",
            version="0.8.12",
        )

    @pytest.fixture(scope="session")
    def borrower_contract(
        self, request, evm_loader, operator_keypair, sender_with_tokens, neon_rpc_client, treasury_pool
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "neon_evm/flash_loan/borrower.sol",
            neon_rpc_client,
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
        neon_rpc_client,
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
        emulate_result = neon_rpc_client.emulate_contract_call(
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
        second_holder_acc,
        holder_acc,
        neon_rpc_client,
        session_user,
        sol_client,
    ):
        data_storage_acc_count = 4
        user1 = session_user
        user2 = user_account
        holder1 = holder_acc
        holder2 = second_holder_acc
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
        emulate_result1 = neon_rpc_client.emulate_contract_call(
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

        emulate_result2 = neon_rpc_client.emulate_contract_call(
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
        second_holder_acc,
        holder_acc,
        neon_rpc_client,
        rw_lock_contract,
        session_user,
        storage_data_len,
        expected_count_data_acc,
        sol_client,
    ):
        user1 = session_user
        user2 = user_account
        holder1 = holder_acc
        holder2 = second_holder_acc
        text1 = "a" * storage_data_len
        text2 = "b" * storage_data_len
        cell_count = (storage_data_len + 31) // 32
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

        emulate_result1 = neon_rpc_client.emulate_contract_call(
            user1.eth_address.hex(), rw_lock_contract.eth_address.hex(), "update_storage_str(string)", [text1]
        )

        acc_from_emulation1 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result1["solana_accounts"]]
        signed_tx1 = make_contract_call_trx(evm_loader, user1, rw_lock_contract, "update_storage_str(string)", [text1])

        evm_loader.write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)

        emulate_result2 = neon_rpc_client.emulate_contract_call(
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
            assert data_acc_revision_after_user1_finished == (cell_count * 1)

        # repeat steps for second user because revision for data accounts is changed
        resp2 = send_transaction_steps(holder2, acc_from_emulation2)
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp2, text="exit_status=0x11")

        if expected_count_data_acc > 0:
            data_acc_revision_after_user2_finished = evm_loader.get_data_account_revision(data_account)
            assert data_acc_revision_after_user2_finished == (cell_count * 2)

    def test_2_users_sent_neons_to_the_same_recipients(
        self,
        operator_keypair,
        treasury_pool,
        neon_rpc_client,
        session_user,
        sender_with_tokens,
        evm_loader,
        holder_acc,
        second_holder_acc,
        sol_client,
        transfers_contract,
    ):
        sender1 = session_user
        sender2 = sender_with_tokens
        holder1 = holder_acc
        holder2 = second_holder_acc
        amount = 1000000
        evm_loader.deposit_neon(operator_keypair, sender1.eth_address, 3 * amount)
        recipients = [
            evm_loader.make_new_user(operator_keypair),
            evm_loader.make_new_user(operator_keypair),
            evm_loader.make_new_user(operator_keypair),
        ]

        recipients_eth_addresses = [rec.eth_address for rec in recipients]
        signed_tx1 = make_contract_call_trx(
            evm_loader,
            sender1,
            transfers_contract,
            "transferNeon(uint256,address[])",
            [amount, recipients_eth_addresses],
            value=3 * amount,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)
        signed_tx2 = make_contract_call_trx(
            evm_loader,
            sender2,
            transfers_contract,
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
                transfers_contract.balance_account_address,
                transfers_contract.solana_address,
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
        neon_rpc_client,
        session_user,
        rw_lock_contract,
        user_account,
        evm_loader,
        holder_acc,
        second_holder_acc,
    ):
        additional_accounts = [session_user.balance_account_address, rw_lock_contract.solana_address]
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        emulate_result = neon_rpc_client.emulate_contract_call(
            session_user.eth_address.hex(),
            rw_lock_contract.eth_address.hex(),
            "update_storage_map_with_salt(uint256,uint256)",
            [3, 1],
        )
        acc_from_emulation = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        data_accounts = list(set(acc_from_emulation) - set(additional_accounts))
        data_acc_revision_before = []
        for acc in data_accounts:
            if evm_loader.get_solana_balance(acc) > 0:
                data_acc_revision_before.append(evm_loader.get_data_account_revision(acc))
            else:
                data_acc_revision_before.append(0)

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

        signed_tx2 = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "update_storage_map_with_salt(uint256,uint256)", [3, 1]
        )
        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            second_holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx2,
            acc_from_emulation,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            acc_from_emulation,
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
        data_acc_revision_after = []
        for acc in data_accounts:
            if evm_loader.get_solana_balance(acc) > 0:
                data_acc_revision_after.append(evm_loader.get_data_account_revision(acc))
            else:
                data_acc_revision_after.append(0)
        assert data_acc_revision_after == [r + 1 for r in data_acc_revision_before]

    def test_1_user_send_2_parallel_trx_with_neon_balance_change(
        self,
        operator_keypair,
        treasury_pool,
        neon_rpc_client,
        session_user,
        evm_loader,
        holder_acc,
        second_holder_acc,
        transfers_contract,
    ):
        amount = 1000000
        evm_loader.deposit_neon(operator_keypair, session_user.eth_address, 4 * amount)
        sender_balance_before = evm_loader.get_neon_balance(session_user.eth_address)

        recipients = [evm_loader.make_new_user(operator_keypair), evm_loader.make_new_user(operator_keypair)]
        recipients_eth_addresses = [rec.eth_address for rec in recipients]

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        signed_tx1 = make_contract_call_trx(
            evm_loader,
            session_user,
            transfers_contract,
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
            transfers_contract.balance_account_address,
            transfers_contract.solana_address,
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
            transfers_contract,
            "transferNeon(uint256,address[])",
            [amount, recipients_eth_addresses],
            value=amount * 2,
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair, second_holder_acc, treasury_pool.account, treasury_pool.buffer, signed_tx2, accounts
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
        neon_rpc_client,
        session_user,
        evm_loader,
        second_holder_acc,
        holder_acc,
        transfers_contract,
    ):
        sender = evm_loader.make_new_user(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        recipient = session_user
        evm_loader.deposit_neon(operator_keypair, sender.eth_address, 1000000)

        amount = evm_loader.get_neon_balance(sender.eth_address)

        signed_tx1 = make_contract_call_trx(
            evm_loader,
            sender,
            transfers_contract,
            "transferNeon(uint256,address[])",
            [amount // 2, [recipient.eth_address]],
            value=amount // 2,
        )
        accounts = [
            sender.balance_account_address,
            sender.solana_account_address,
            transfers_contract.balance_account_address,
            transfers_contract.solana_address,
            recipient.balance_account_address,
            recipient.solana_account_address,
        ]

        evm_loader.write_transaction_to_holder_account(signed_tx1, second_holder_acc, operator_keypair)
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            second_holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            second_holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )

        signed_tx2 = make_contract_call_trx(
            evm_loader,
            sender,
            transfers_contract,
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
                second_holder_acc,
                accounts,
                EVM_STEPS,
                operator_keypair,
            )
        evm_loader.send_cancel_transaction(operator_keypair, second_holder_acc, accounts, signed_tx1.hash)

    def test_parallel_change_balance_in_one_trx_and_check_in_second_trx(
        self,
        operator_keypair,
        treasury_pool,
        neon_rpc_client,
        sender_with_tokens,
        evm_loader,
        holder_acc,
        second_holder_acc,
    ):
        contract = evm_loader.deploy_contract(
            operator_keypair, sender_with_tokens, "transfers", neon_rpc_client, treasury_pool, value=1000
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
        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair, second_holder_acc, treasury_pool.account, treasury_pool.buffer, signed_tx2, accounts
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        # To finish after RESET we only need one interation, because there are no state change
        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )

        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="RESET")
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
        neon_rpc_client,
        treasury_pool,
        holder_acc,
        second_holder_acc,
        func_signature,
        amount_emulated_accounts,
        second_session_user,
    ):
        func1_args = [15]
        emulate_result = neon_rpc_client.emulate_contract_call(
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
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        # start first tx
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            emulated_accounts,
            EVM_STEPS,
            operator_keypair,
        )

        # make second transaction, change  number value and back original value in the same tx
        func2_args = [2]
        emulate_result2 = neon_rpc_client.emulate_contract_call(
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
        evm_loader.write_transaction_to_holder_account(signed_tx2, second_holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, second_holder_acc, emulated_accounts_2
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        # finish the first tx
        final_receipt = None
        for _ in range(4):
            final_receipt = evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder_acc,
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
        neon_rpc_client,
        treasury_pool,
        holder_acc,
        second_holder_acc,
        second_session_user,
    ):

        # First tx prepare
        func_signature = "powAmount(uint256,uint256)"
        func1_args = [5, 10]

        emulate_result = neon_rpc_client.emulate_contract_call(
            second_session_user.eth_address.hex(), lender_contract.eth_address.hex(), func_signature, func1_args
        )

        emulated_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        signed_tx = make_contract_call_trx(evm_loader, second_session_user, lender_contract, func_signature, func1_args)

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        evm_loader.write_transaction_to_holder_account(signed_tx, second_holder_acc, operator_keypair)

        for i in range(2):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                second_holder_acc,
                emulated_accounts,
                EVM_STEPS,
                operator_keypair,
            )

        # second tx
        func2_signature = "flashLoan(address,uint256)"
        func2_args = [borrower_contract.eth_address, 9]

        emulate_result_2 = neon_rpc_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(), lender_contract.eth_address.hex(), func2_signature, func2_args, "0x9"
        )

        emulated_accounts_2 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result_2["solana_accounts"]]
        signed_tx2 = make_contract_call_trx(
            evm_loader, sender_with_tokens, lender_contract, func2_signature, func2_args, 9
        )

        evm_loader.write_transaction_to_holder_account(signed_tx2, holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder_acc, emulated_accounts_2
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")
        # finish first tx
        resp = None
        for i in range(2):
            resp = evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                second_holder_acc,
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
        neon_rpc_client,
        treasury_pool,
        holder_acc,
    ):

        balance_before = evm_loader.get_neon_balance(lender_contract.eth_address, evm_loader.chain_id)
        revision_before = evm_loader.get_balance_account_revision(lender_contract.balance_account_address)

        func_signature = "flashLoan(address,uint256)"
        func_args = [borrower_contract.eth_address, 9]

        emulate_result = neon_rpc_client.emulate_contract_call(
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

        evm_loader.write_transaction_to_holder_account(signed_tx2, holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder_acc, emulated_accounts
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
        second_holder_acc,
        holder_acc,
        neon_rpc_client,
        revision_contract,
        revision_contract_caller,
        session_user,
        sol_client,
    ):
        contract_revision_before = evm_loader.get_contract_account_revision(revision_contract.solana_address)
        contract_revision_caller_before = evm_loader.get_contract_account_revision(
            revision_contract_caller.solana_address
        )
        user1 = session_user
        user2 = user_account
        holder1 = holder_acc
        holder2 = second_holder_acc
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        additional_accounts = [
            session_user.balance_account_address,
            revision_contract.solana_address,
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

        emulate_result1 = neon_rpc_client.emulate_contract_call(
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

        emulate_result2 = neon_rpc_client.emulate_contract_call(
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

        contract_revision_after = evm_loader.get_contract_account_revision(revision_contract.solana_address)
        contract_revision_caller_after = evm_loader.get_contract_account_revision(
            revision_contract_caller.solana_address
        )
        assert contract_revision_before == contract_revision_after - (63 * 2)
        assert contract_revision_caller_before == contract_revision_caller_after

        data_accounts = set(acc_from_emulation1) - set(additional_accounts)
        for acc in data_accounts:
            data_acc_revision_after = evm_loader.get_data_account_revision(acc)
            assert data_acc_revision_after == 3

    def test_revision_changed_by_iterative_second_trx_with_solana_call(
        self,
        evm_loader,
        operator_keypair,
        treasury_pool,
        second_holder_acc,
        holder_acc,
        neon_rpc_client,
        revision_with_solana_call_contract,
        session_user,
        sender_with_tokens,
        environment,
    ):
        holder1 = holder_acc
        holder2 = second_holder_acc
        recipient = session_user
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        balance_account_revision = evm_loader.get_balance_account_revision(
            revision_with_solana_call_contract.balance_account_address
        )
        amount = 10000

        signed_tx1 = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            revision_with_solana_call_contract,
            "transferNeonSeveralTimes(uint256,address)",
            [10, recipient.eth_address],
            value=10 * amount,
        )

        accounts_from_emulation1 = neon_rpc_client.get_additional_accounts_by_emulation(
            sender_with_tokens.eth_address.hex(),
            revision_with_solana_call_contract.eth_address.hex(),
            "transferNeonSeveralTimes(uint256,address)",
            [10, recipient.eth_address],
            value=hex(10 * amount),
        )

        evm_loader.write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)

        for _ in range(25):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder1,
                accounts_from_emulation1,
                EVM_STEPS,
                operator_keypair,
            )

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder1,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_ACTIVE_STATE,
        )

        recipient_balance_before_trx2 = evm_loader.get_neon_balance(recipient.eth_address)
        payer_bytes32 = neon_rpc_client.call_contract_get_function(
            sender_with_tokens, revision_with_solana_call_contract, "getPayer()"
        )
        payer = bytes32_to_solana_pubkey(payer_bytes32)

        instruction = make_create_associated_token_idempotent(
            payer, sender_with_tokens.solana_account_address, Pubkey.from_string(environment.spl_neon_mint)
        )
        serialized_instructions = serialize_instruction(ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID, instruction)

        signed_tx2 = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            revision_with_solana_call_contract,
            "transferNeonAndCallSolana(uint64,bytes,uint256,address)",
            [2039280, serialized_instructions, amount, recipient.eth_address],
            value=2 * amount,
        )

        accounts_from_emulation2 = neon_rpc_client.get_additional_accounts_by_emulation(
            sender_with_tokens.eth_address.hex(),
            revision_with_solana_call_contract.eth_address.hex(),
            "transferNeonAndCallSolana(uint64,bytes,uint256,address)",
            [2039280, serialized_instructions, amount, recipient.eth_address],
            value=hex(2 * amount),
        )

        evm_loader.write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

        # iterative execution of trx2
        resp2 = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder2, accounts_from_emulation2
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp2, text="exit_status=0x11")

        payer_info = evm_loader.get_account_info(payer, commitment=Confirmed)
        assert payer_info.value is None

        # rerun trx1
        resp1 = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder1, accounts_from_emulation1, check_invalid_revision=True
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp1, text="exit_status=0x11")

        recipient_balance_after_trx1_rerun = evm_loader.get_neon_balance(recipient.eth_address)
        assert recipient_balance_after_trx1_rerun == recipient_balance_before_trx2 + 2 * amount + 10 * amount
        assert evm_loader.get_neon_balance(revision_with_solana_call_contract.eth_address) == 0

        balance_account_revision_after = evm_loader.get_balance_account_revision(
            revision_with_solana_call_contract.balance_account_address
        )
        assert balance_account_revision_after == balance_account_revision + 2

    def test_revision_changed_by_non_iterative_second_trx_with_solana_call(
        self,
        evm_loader,
        operator_keypair,
        treasury_pool,
        holder_acc,
        second_holder_acc,
        neon_rpc_client,
        revision_with_solana_call_contract,
        session_user,
        sol_client,
        environment,
        sender_with_tokens,
    ):
        holder1 = holder_acc
        holder2 = second_holder_acc
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        recipient = session_user
        amount1 = 10000
        amount2 = amount1 // 2

        balance_account_revision_before = evm_loader.get_balance_account_revision(
            revision_with_solana_call_contract.balance_account_address
        )
        recipient_balance_before = evm_loader.get_neon_balance(recipient.eth_address)

        signed_tx1 = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            revision_with_solana_call_contract,
            "transferNeonSeveralTimes(uint256,address)",
            [10, recipient.eth_address],
            value=10 * amount1,
        )

        emulate_result = neon_rpc_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(),
            revision_with_solana_call_contract.eth_address.hex(),
            "transferNeonSeveralTimes(uint256,address)",
            [10, recipient.eth_address],
            value=hex(10 * amount1),
        )

        accounts_from_emulation1 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        evm_loader.write_transaction_to_holder_account(signed_tx1, holder1, operator_keypair)

        for _ in range(25):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder1,
                accounts_from_emulation1,
                EVM_STEPS,
                operator_keypair,
            )

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder1,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_ACTIVE_STATE,
        )

        payer_bytes32 = neon_rpc_client.call_contract_get_function(
            sender_with_tokens, revision_with_solana_call_contract, "getPayer()"
        )
        payer = bytes32_to_solana_pubkey(payer_bytes32)

        instruction = make_create_associated_token_idempotent(
            payer, sender_with_tokens.solana_account_address, Pubkey.from_string(environment.spl_neon_mint)
        )
        serialized_instructions = serialize_instruction(ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID, instruction)

        signed_tx2 = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            revision_with_solana_call_contract,
            "transferNeonAndCallSolana(uint64,bytes,uint256,address)",
            [2039280, serialized_instructions, amount2, recipient.eth_address],
            value=amount2 * 2,
        )

        emulate_result = neon_rpc_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(),
            revision_with_solana_call_contract.eth_address.hex(),
            "transferNeonAndCallSolana(uint64,bytes,uint256,address)",
            [2039280, serialized_instructions, amount2, recipient.eth_address],
            value=hex(amount2 * 2),
        )

        accounts_from_emulation2 = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        evm_loader.write_transaction_to_holder_account(signed_tx2, holder2, operator_keypair)

        # non iterative execution of trx2
        resp2 = evm_loader.execute_trx_from_account_with_solana_call(
            operator_keypair, holder2, treasury_pool.account, treasury_pool.buffer, accounts_from_emulation2
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp2, text="exit_status=0x11")

        payer_info = evm_loader.get_account_info(payer, commitment=Confirmed)
        assert payer_info.value is None

        resp1 = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder1, accounts_from_emulation1
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp1, text="exit_status=0x11")

        assert recipient_balance_before + 2 * amount2 + 10 * amount1 == evm_loader.get_neon_balance(
            recipient.eth_address
        )
        assert evm_loader.get_neon_balance(revision_with_solana_call_contract.eth_address) == 0
        balance_account_revision = evm_loader.get_balance_account_revision(
            revision_with_solana_call_contract.balance_account_address
        )
        assert balance_account_revision == balance_account_revision_before + 3
