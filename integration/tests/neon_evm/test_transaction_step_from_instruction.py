import random
import string

import eth_abi
import pytest
import rlp
import solana
import solders.system_program as sp
from eth_account.datastructures import SignedTransaction
from eth_keys import keys as eth_keys
from eth_utils import abi, to_text, to_int
from hexbytes import HexBytes
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.core import RPCException

from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from utils.types import TreasuryPool
from .utils.assert_messages import InstructionAsserts

from .utils.constants import TAG_FINALIZED_STATE, TAG_ACTIVE_STATE

from .utils.ethereum import (
    make_eth_transaction,
    create_contract_address,
    make_contract_call_trx,
    make_deployment_transaction,
)
from .utils.transaction_checks import check_transaction_logs_have_text, check_holder_account_tag


class TestTransactionStepFromInstruction:
    def test_simple_transfer_transaction(
        self,
        operator_keypair,
        treasury_pool,
        evm_loader,
        sender_with_tokens,
        session_user,
        holder_acc,
        sol_client,
    ):
        amount = 10
        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        recipient_balance_before = evm_loader.get_neon_balance(session_user.eth_address)

        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, amount)

        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                session_user.solana_account_address,
                session_user.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )

        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        recipient_balance_after = evm_loader.get_neon_balance(session_user.eth_address)

        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x11")
        assert sender_balance_before - amount == sender_balance_after
        assert recipient_balance_before + amount == recipient_balance_after

    @pytest.mark.parametrize("chain_id", [None, 111])
    def test_deploy_contract(
        self,
        operator_keypair,
        holder_acc,
        treasury_pool,
        evm_loader,
        sender_with_tokens,
        chain_id,
        sol_client,
    ):
        contract_filename = "small"

        signed_tx = make_deployment_transaction(evm_loader, sender_with_tokens, contract_filename, chain_id=chain_id)
        contract = create_contract_address(sender_with_tokens, evm_loader)

        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                contract.solana_address,
                contract.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )

        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x12")

    def test_call_contract_function_without_neon_transfer(
        self,
        operator_keypair,
        treasury_pool,
        sender_with_tokens,
        evm_loader,
        holder_acc,
        string_setter_contract,
        neon_api_client,
    ):
        text = "".join(random.choice(string.ascii_letters) for _ in range(10))
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, string_setter_contract, "set(string)", [text]
        )

        additional_accounts = neon_api_client.get_additional_accounts_by_emulation(
            sender_with_tokens.eth_address.hex(), string_setter_contract.eth_address.hex(), "set(string)", params=[text]
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
        )

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        assert text in to_text(
            neon_api_client.call_contract_get_function(sender_with_tokens, string_setter_contract, "get()")
        )

    def test_call_contract_function_with_neon_transfer(
        self,
        operator_keypair,
        treasury_pool,
        sender_with_tokens,
        evm_loader,
        holder_acc,
        string_setter_contract,
        neon_api_client,
    ):
        transfer_amount = random.randint(1, 1000)

        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        contract_balance_before = evm_loader.get_neon_balance(string_setter_contract.eth_address)

        text = "".join(random.choice(string.ascii_letters) for _ in range(10))
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, string_setter_contract, "set(string)", [text], value=transfer_amount
        )

        additional_accounts = neon_api_client.get_additional_accounts_by_emulation(
            sender_with_tokens.eth_address.hex(),
            string_setter_contract.eth_address.hex(),
            "set(string)",
            params=[text],
            value=transfer_amount,
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
        )

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        contract_balance_after = evm_loader.get_neon_balance(string_setter_contract.eth_address)
        assert sender_balance_before - transfer_amount == sender_balance_after
        assert contract_balance_before + transfer_amount == contract_balance_after

        assert text in to_text(
            neon_api_client.call_contract_get_function(sender_with_tokens, string_setter_contract, "get()")
        )

    def test_transfer_transaction_with_non_existing_recipient(
        self, operator_keypair, treasury_pool, sender_with_tokens, evm_loader, holder_acc, sol_client
    ):
        # recipient account should be created
        recipient = Keypair()
        recipient_ether = eth_keys.PrivateKey(recipient.secret()[:32]).public_key.to_canonical_address()
        recipient_solana_address, _ = evm_loader.ether2program(recipient_ether)
        recipient_balance_address = evm_loader.ether2balance(recipient_ether)
        amount = 10
        signed_tx = make_eth_transaction(evm_loader, recipient_ether, None, sender_with_tokens, amount)

        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                Pubkey.from_string(recipient_solana_address),
                recipient_balance_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )

        recipient_balance_after = evm_loader.get_neon_balance(recipient_ether)
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x11")

        assert recipient_balance_after == amount

    def test_incorrect_chain_id(
        self, operator_keypair, holder_acc, treasury_pool, sender_with_tokens, session_user, evm_loader
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1, chain_id=1)

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.INVALID_CHAIN_ID):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_incorrect_nonce(
        self, operator_keypair, treasury_pool, sender_with_tokens, evm_loader, session_user, holder_acc, temp_holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                session_user.solana_account_address,
                session_user.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.INVALID_NONCE):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                temp_holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_run_finalized_transaction(
        self, operator_keypair, treasury_pool, sender_with_tokens, evm_loader, session_user, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                session_user.solana_account_address,
                session_user.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.TRX_ALREADY_FINALIZED):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_insufficient_funds(
        self, operator_keypair, treasury_pool, evm_loader, session_user, holder_acc, sender_with_tokens
    ):
        user_balance = evm_loader.get_neon_balance(session_user.eth_address)

        signed_tx = make_eth_transaction(
            evm_loader, sender_with_tokens.eth_address, None, session_user, user_balance + 1
        )

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.INSUFFICIENT_FUNDS):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_gas_limit_reached(
        self, operator_keypair, treasury_pool, session_user, evm_loader, sender_with_tokens, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 10, gas=1)

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.OUT_OF_GAS):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_sender_missed_in_remaining_accounts(
        self, operator_keypair, treasury_pool, session_user, sender_with_tokens, evm_loader, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.ADDRESS_MUST_BE_PRESENT):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                holder_acc,
                signed_tx,
                [session_user.solana_account_address, session_user.balance_account_address],
            )

    def test_recipient_missed_in_remaining_accounts(
        self, operator_keypair, treasury_pool, session_user, sender_with_tokens, evm_loader, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.ADDRESS_MUST_BE_PRESENT):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                holder_acc,
                signed_tx,
                [session_user.solana_account_address, session_user.balance_account_address],
            )

    def test_incorrect_treasure_pool(self, operator_keypair, sender_with_tokens, evm_loader, session_user, holder_acc):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        index = 2
        treasury = TreasuryPool(index, Keypair().pubkey(), index.to_bytes(4, "little"))

        error = str.format(InstructionAsserts.INVALID_ACCOUNT, treasury.account)
        with pytest.raises(solana.rpc.core.RPCException, match=error):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury,
                holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_incorrect_treasure_index(self, operator_keypair, sender_with_tokens, evm_loader, session_user, holder_acc):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        index = 2
        treasury = TreasuryPool(
            index, evm_loader.create_treasury_pool_address(index), (index + 98).to_bytes(4, "little")
        )

        error = str.format(InstructionAsserts.INVALID_ACCOUNT, treasury.account)
        with pytest.raises(solana.rpc.core.RPCException, match=error):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury,
                holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_incorrect_operator_account(self, sender_with_tokens, evm_loader, treasury_pool, session_user, holder_acc):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        fake_operator = Keypair()
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.INCORRECT_OPERATOR):
            evm_loader.execute_transaction_steps_from_instruction(
                fake_operator,
                treasury_pool,
                holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_operator_is_not_in_white_list(
        self, sender_with_tokens, evm_loader, treasury_pool, session_user, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.NOT_AUTHORIZED_OPERATOR):
            evm_loader.execute_transaction_steps_from_instruction(
                sender_with_tokens.solana_account,
                treasury_pool,
                holder_acc,
                signed_tx,
                [
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )

    def test_incorrect_system_program(
        self, sender_with_tokens, operator_keypair, evm_loader, treasury_pool, session_user, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        fake_sys_program_id = Keypair().pubkey()
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
        with pytest.raises(solana.rpc.core.RPCException, match=str.format(InstructionAsserts.ACCOUNT_NOT_FOUND, sp.ID)):
            evm_loader.send_transaction_step_from_instruction(
                operator_keypair,
                operator_balance,
                treasury_pool,
                holder_acc,
                signed_tx,
                [
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                ],
                1,
                operator_keypair,
                system_program=fake_sys_program_id,
            )

    def test_incorrect_holder_account(
        self, sender_with_tokens, operator_keypair, evm_loader, treasury_pool, session_user
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        fake_holder_acc = Keypair().pubkey()
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
        with pytest.raises(
            solana.rpc.core.RPCException, match=str.format(InstructionAsserts.NOT_PROGRAM_OWNED, fake_holder_acc)
        ):
            evm_loader.send_transaction_step_from_instruction(
                operator_keypair,
                operator_balance,
                treasury_pool,
                fake_holder_acc,
                signed_tx,
                [
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                    session_user.solana_account_address,
                    session_user.balance_account_address,
                ],
                1,
                operator_keypair,
            )

    @pytest.mark.parametrize("value", [0, 10])
    def test_transaction_with_access_list(
        self,
        operator_keypair,
        treasury_pool,
        sender_with_tokens,
        evm_loader,
        holder_acc,
        string_setter_contract,
        neon_api_client,
        value,
    ):
        access_list = (
            {
                "address": "0x" + string_setter_contract.eth_address.hex(),
                "storageKeys": (
                    "0x0000000000000000000000000000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000000000000000000000000000001",
                ),
            },
        )
        signed_tx = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            string_setter_contract,
            "set(string)",
            ["text"],
            value=value,
            access_list=access_list,
        )
        additional_accounts = neon_api_client.get_additional_accounts_by_emulation(
            sender_with_tokens.eth_address.hex(),
            string_setter_contract.eth_address.hex(),
            "set(string)",
            params=["text"],
            value=value,
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
        )

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

    def test_deploy_contract_with_access_list(
        self,
        operator_keypair,
        holder_acc,
        treasury_pool,
        evm_loader,
        sender_with_tokens,
        neon_api_client,
        sol_client,
    ):
        contract_filename = "small"
        contract = create_contract_address(sender_with_tokens, evm_loader)

        access_list = (
            {
                "address": contract.eth_address.hex(),
                "storageKeys": ("0x0000000000000000000000000000000000000000000000000000000000000000",),
            },
        )
        signed_tx = make_deployment_transaction(
            evm_loader, sender_with_tokens, contract_filename, access_list=access_list
        )

        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                contract.solana_address,
                contract.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x12")


class TestInstructionStepContractCallContractInteractions:
    def test_contract_call_unchange_storage_function(
        self,
        rw_lock_contract,
        session_user,
        evm_loader,
        operator_keypair,
        treasury_pool,
        holder_acc,
        rw_lock_caller,
        sol_client,
    ):
        signed_tx = make_contract_call_trx(
            evm_loader, session_user, rw_lock_caller, "unchange_storage(uint8,uint8)", [1, 1]
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            [
                rw_lock_caller.solana_address,
                rw_lock_contract.solana_address,
                session_user.solana_account_address,
                session_user.balance_account_address,
            ],
        )

        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x12")

    def test_contract_call_set_function(
        self,
        rw_lock_contract,
        session_user,
        evm_loader,
        operator_keypair,
        treasury_pool,
        holder_acc,
        rw_lock_caller,
        neon_api_client,
    ):
        text = "".join(random.choice(string.ascii_letters) for _ in range(10))
        signed_tx = make_contract_call_trx(
            evm_loader, session_user, rw_lock_caller, "update_storage_str(string)", [text]
        )
        additional_accounts = neon_api_client.get_additional_accounts_by_emulation(
            session_user.eth_address.hex(),
            rw_lock_caller.eth_address.hex(),
            "update_storage_str(string)",
            params=[text],
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
        )

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        assert text in to_text(neon_api_client.call_contract_get_function(session_user, rw_lock_contract, "get_text()"))

    def test_contract_call_get_function(
        self,
        rw_lock_contract,
        session_user,
        evm_loader,
        operator_keypair,
        treasury_pool,
        holder_acc,
        rw_lock_caller,
        neon_api_client,
    ):
        signed_tx = make_contract_call_trx(evm_loader, session_user, rw_lock_caller, "get_text()")
        additional_accounts = neon_api_client.get_additional_accounts_by_emulation(
            session_user.eth_address.hex(), rw_lock_caller.eth_address.hex(), "get_text()"
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair, treasury_pool, holder_acc, signed_tx, additional_accounts
        )

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x12")

    def test_contract_call_update_storage_map_function(
        self,
        rw_lock_contract,
        session_user,
        evm_loader,
        operator_keypair,
        rw_lock_caller,
        treasury_pool,
        holder_acc,
        neon_api_client,
    ):
        signed_tx = make_contract_call_trx(evm_loader, session_user, rw_lock_caller, "update_storage_map(uint256)", [3])

        func_name = abi.function_signature_to_4byte_selector("update_storage_map(uint256)")
        data = func_name + eth_abi.encode(["uint256"], [3])
        result = neon_api_client.emulate(session_user.eth_address.hex(), rw_lock_caller.eth_address.hex(), data)
        additional_accounts = [
            session_user.solana_account_address,
            session_user.balance_account_address,
            rw_lock_contract.solana_address,
            rw_lock_caller.solana_address,
        ]
        for acc in result["solana_accounts"]:
            additional_accounts.append(Pubkey.from_string(acc["pubkey"]))

        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair, treasury_pool, holder_acc, signed_tx, additional_accounts
        )

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        constructor_args = eth_abi.encode(["address", "uint256"], [rw_lock_caller.eth_address.hex(), 2])
        actual_data = neon_api_client.call_contract_get_function(
            session_user, rw_lock_contract, "data(address,uint256)", constructor_args
        )
        assert to_int(hexstr=actual_data) == 2, "Contract data is not correct"


class TestTransactionStepFromInstructionParallelRuns:
    def test_one_user_call_2_contracts(
        self,
        rw_lock_contract,
        string_setter_contract,
        session_user,
        evm_loader,
        operator_keypair,
        treasury_pool,
        holder_acc,
        second_holder_acc,
    ):
        signed_tx = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
        )
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)

        def send_transaction_steps(holder_acc, contract, trx):
            evm_loader.send_transaction_step_from_instruction(
                operator_keypair,
                operator_balance,
                treasury_pool,
                holder_acc,
                trx,
                [session_user.solana_account_address, session_user.balance_account_address, contract.solana_address],
                500,
                operator_keypair,
            )

        send_transaction_steps(second_holder_acc, rw_lock_contract, signed_tx)

        signed_tx2 = make_contract_call_trx(evm_loader, session_user, string_setter_contract, "get()")

        send_transaction_steps(holder_acc, string_setter_contract, signed_tx2)
        send_transaction_steps(second_holder_acc, rw_lock_contract, signed_tx)
        send_transaction_steps(holder_acc, string_setter_contract, signed_tx2)
        send_transaction_steps(second_holder_acc, rw_lock_contract, signed_tx)
        send_transaction_steps(holder_acc, string_setter_contract, signed_tx2)

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=second_holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_ACTIVE_STATE,
        )
        send_transaction_steps(holder_acc, string_setter_contract, signed_tx2)
        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_2_users_call_the_same_contract(
        self,
        rw_lock_contract,
        second_session_user,
        session_user,
        evm_loader,
        operator_keypair,
        treasury_pool,
        second_holder_acc,
        holder_acc,
        neon_api_client,
    ):
        signed_tx = make_contract_call_trx(
            evm_loader, second_session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
        )
        additional_accounts_trx1 = neon_api_client.get_additional_accounts_by_emulation(
            second_session_user.eth_address.hex(),
            rw_lock_contract.eth_address.hex(),
            "unchange_storage(uint8,uint8)",
            [1, 1],
        )
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)

        def send_transaction_steps(holder_address, trx, additional_accounts):
            evm_loader.send_transaction_step_from_instruction(
                operator_keypair,
                operator_balance,
                treasury_pool,
                holder_address,
                trx,
                additional_accounts,
                500,
                operator_keypair,
            )

        send_transaction_steps(second_holder_acc, signed_tx, additional_accounts_trx1)

        signed_tx2 = make_contract_call_trx(evm_loader, session_user, rw_lock_contract, "get_text()")
        additional_accounts_trx2 = neon_api_client.get_additional_accounts_by_emulation(
            session_user.eth_address.hex(), rw_lock_contract.eth_address.hex(), "get_text()"
        )
        send_transaction_steps(holder_acc, signed_tx2, additional_accounts_trx2)
        send_transaction_steps(second_holder_acc, signed_tx, additional_accounts_trx1)
        send_transaction_steps(holder_acc, signed_tx2, additional_accounts_trx2)
        send_transaction_steps(second_holder_acc, signed_tx, additional_accounts_trx1)
        send_transaction_steps(holder_acc, signed_tx2, additional_accounts_trx2)
        for holder in (second_holder_acc, holder_acc):
            check_holder_account_tag(
                solana_client=evm_loader,
                storage_account=holder,
                layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
                expected_tag=TAG_FINALIZED_STATE,
            )

    def test_two_contracts_call_same_contract(
        self,
        rw_lock_contract,
        session_user,
        evm_loader,
        operator_keypair,
        treasury_pool,
        holder_acc,
        second_holder_acc,
        neon_api_client,
        rw_lock_caller,
    ):

        signed_tx1 = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
        )
        additional_accounts_trx1 = neon_api_client.get_additional_accounts_by_emulation(
            session_user.eth_address.hex(), rw_lock_contract.eth_address.hex(), "unchange_storage(uint8,uint8)", [1, 1]
        )

        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)

        def send_transaction_steps(holder_address, trx, additional_accounts):
            evm_loader.send_transaction_step_from_instruction(
                operator_keypair,
                operator_balance,
                treasury_pool,
                holder_address,
                trx,
                additional_accounts,
                500,
                operator_keypair,
            )

        send_transaction_steps(second_holder_acc, signed_tx1, additional_accounts_trx1)
        signed_tx2 = make_contract_call_trx(evm_loader, session_user, rw_lock_caller, "get_text()")
        additional_accounts_trx2 = neon_api_client.get_additional_accounts_by_emulation(
            session_user.eth_address.hex(), rw_lock_caller.eth_address.hex(), "get_text()"
        )
        send_transaction_steps(holder_acc, signed_tx2, additional_accounts_trx2)
        send_transaction_steps(second_holder_acc, signed_tx1, additional_accounts_trx1)
        send_transaction_steps(holder_acc, signed_tx2, additional_accounts_trx2)

        evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            second_holder_acc,
            signed_tx1,
            additional_accounts_trx1,
        )
        evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx2,
            additional_accounts_trx2,
        )

        for holder in (second_holder_acc, holder_acc):
            check_holder_account_tag(
                solana_client=evm_loader,
                storage_account=holder,
                layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
                expected_tag=TAG_FINALIZED_STATE,
            )


class TestStepFromInstructionChangingOperatorsDuringTrxRun:
    def test_next_operator_can_continue_trx(
        self,
        rw_lock_contract,
        session_user,
        evm_loader,
        operator_keypair,
        second_operator_keypair,
        treasury_pool,
        holder_acc,
        neon_api_client,
    ):
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
        second_operator_balance = evm_loader.get_operator_balance_pubkey(second_operator_keypair)
        signed_tx = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "update_storage_str(string)", ["text"]
        )
        additional_accounts = neon_api_client.get_additional_accounts_by_emulation(
            session_user.eth_address.hex(), rw_lock_contract.eth_address.hex(), "update_storage_str(string)", ["text"]
        )

        evm_loader.send_transaction_step_from_instruction(
            operator_keypair,
            operator_balance,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
            1,
            operator_keypair,
        )

        # send from the second operator
        evm_loader.send_transaction_step_from_instruction(
            second_operator_keypair,
            second_operator_balance,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
            500,
            second_operator_keypair,
        )
        resp = evm_loader.send_transaction_step_from_instruction(
            second_operator_keypair,
            second_operator_balance,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
            1,
            second_operator_keypair,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")


class TestStepFromInstructionWithChangedRLPTrx:
    def test_add_waste_to_trx(
        self, sender_with_tokens, operator_keypair, treasury_pool, evm_loader, holder_acc, string_setter_contract
    ):
        text = "".join(random.choice(string.ascii_letters) for _ in range(10))
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, string_setter_contract, "set(string)", [text]
        )
        decoded_tx = rlp.decode(signed_tx.raw_transaction)
        decoded_tx.insert(6, HexBytes(b"\x19p\x16l\xc0"))
        new_trx = HexBytes(rlp.encode(decoded_tx))

        signed_tx_new = SignedTransaction(
            raw_transaction=new_trx,
            hash=signed_tx.hash,
            r=signed_tx.r,
            s=signed_tx.s,
            v=signed_tx.v,
        )
        with pytest.raises(RPCException, match="Program log: RLP error: RlpIncorrectListLen"):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                holder_acc,
                signed_tx_new,
                [
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                    string_setter_contract.solana_address,
                ],
            )

    def test_add_waste_to_trx_without_decoding(
        self, sender_with_tokens, operator_keypair, treasury_pool, evm_loader, holder_acc, string_setter_contract
    ):
        text = "".join(random.choice(string.ascii_letters) for _ in range(10))
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, string_setter_contract, "set(string)", [text]
        )
        signed_tx_new = SignedTransaction(
            raw_transaction=signed_tx.raw_transaction + HexBytes(b"\x19p\x16l\xc0"),
            hash=signed_tx.hash,
            r=signed_tx.r,
            s=signed_tx.s,
            v=signed_tx.v,
        )
        with pytest.raises(RPCException, match="Program log: RLP error: RlpInconsistentLengthAndData"):
            evm_loader.execute_transaction_steps_from_instruction(
                operator_keypair,
                treasury_pool,
                holder_acc,
                signed_tx_new,
                [
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                    string_setter_contract.solana_address,
                ],
            )

    def test_old_trx_type_with_leading_zeros(
        self,
        sender_with_tokens,
        operator_keypair,
        evm_loader,
        string_setter_contract,
        treasury_pool,
        neon_api_client,
        holder_acc,
    ):
        text = "".join(random.choice(string.ascii_letters) for _ in range(10))

        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, string_setter_contract, "set(string)", [text]
        )
        additional_accounts = neon_api_client.get_additional_accounts_by_emulation(
            sender_with_tokens.eth_address.hex(), string_setter_contract.eth_address.hex(), "set(string)", params=[text]
        )
        new_raw_trx = HexBytes(bytes([0]) + signed_tx.raw_transaction)

        signed_tx_new = SignedTransaction(
            raw_transaction=new_raw_trx,
            hash=signed_tx.hash,
            r=signed_tx.r,
            s=signed_tx.s,
            v=signed_tx.v,
        )
        resp = evm_loader.execute_transaction_steps_from_instruction(
            operator_keypair,
            treasury_pool,
            holder_acc,
            signed_tx_new,
            additional_accounts,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")
