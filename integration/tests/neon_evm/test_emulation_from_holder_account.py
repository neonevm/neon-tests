import random
import pytest

from solders.pubkey import Pubkey
from solana.transaction import Instruction, AccountMeta
from solana.rpc.core import RPCException
from utils.helpers import serialize_instruction
from utils.evm_loader import EVM_STEPS
from utils.consts import REMAPPING_ZEPPELIN, COUNTER_ID
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from .utils.constants import TAG_FINALIZED_STATE
from .utils.contract import get_contract_bin
from .utils.ethereum import make_contract_call_trx
from .utils.transaction_checks import (
    check_holder_account_tag,
    check_transaction_logs_have_text,
)
from .utils import ethereum as eth_utils


class TestEmulateFromHolderAccount:
    @pytest.fixture(scope="class")
    def block_timestamp_contract(
        self, evm_loader, operator_keypair, sender_with_tokens, neon_api_client, treasury_pool
    ):
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "common/Block.sol",
            neon_api_client,
            treasury_pool,
            contract_name="BlockTimestamp",
            version="0.8.10",
        )

    def test_emulate_from_holder_account_contract_function_call(
        self,
        operator_keypair,
        session_user,
        rw_lock_contract,
        neon_api_client,
        evm_loader,
        treasury_pool,
        holder_acc,
    ):
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        signed_tx = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [2, 2]
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        accounts = [
            session_user.balance_account_address,
            rw_lock_contract.solana_address,
        ]

        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
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
        emulate_result = neon_api_client.emulate_from_holder(holder_acc)

        accounts_after_emulation = []
        for item in emulate_result["solana_accounts"]:
            accounts_after_emulation.append(Pubkey.from_string(item["pubkey"]))

        assert sorted(accounts_after_emulation) == sorted(accounts)
        assert emulate_result["exit_status"] == "succeed"
        assert int(emulate_result["result"]) == 4
        assert not emulate_result["external_solana_call"]
        assert not emulate_result["reverts_before_solana_calls"]
        assert not emulate_result["reverts_after_solana_calls"]
        assert not emulate_result["is_timestamp_number_used"]

        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x12")

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_emulate_from_holder_account_contract_deploy(
        self, operator_keypair, sender_with_tokens, neon_api_client, evm_loader, treasury_pool, holder_acc
    ):
        def send_transaction_steps(holder_acc, accounts_from_emulation):
            operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
            return evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder_acc,
                accounts_from_emulation,
                EVM_STEPS,
                operator_keypair,
            )

        chain_id = evm_loader.chain_id
        contract_file_name = "external/neon-contracts/contracts/token/ERC20ForSpl/erc20_for_spl_factory.sol"
        contract_name = "ERC20ForSplFactory"
        version = "0.8.28"

        contract_code = get_contract_bin(
            contract=contract_file_name,
            contract_name=contract_name,
            version=version,
            import_remappings=REMAPPING_ZEPPELIN,
        )

        emulate_result = neon_api_client.emulate(
            sender_with_tokens.eth_address.hex(),
            contract=None,
            data=contract_code,
            chain_id=chain_id,
            value=hex(0),
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        signed_tx = eth_utils.make_deployment_transaction(
            evm_loader,
            sender_with_tokens,
            contract_file_name,
            contract_name,
            value=0,
            version=version,
            chain_id=chain_id,
            import_remappings=REMAPPING_ZEPPELIN,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        send_transaction_steps(holder_acc, additional_accounts)
        send_transaction_steps(holder_acc, additional_accounts)

        emulate_result = neon_api_client.emulate_from_holder(holder_acc)
        assert emulate_result["exit_status"] == "succeed"

        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder_acc, additional_accounts
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x12")

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_emulate_from_holder_account_reverts_check(
        self,
        operator_keypair,
        session_user,
        neon_api_client,
        evm_loader,
        treasury_pool,
        holder_acc,
        transfers_contract,
        solana_caller,
    ):
        recipients = [evm_loader.make_new_user(operator_keypair), evm_loader.make_new_user(operator_keypair)]
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        recipients_eth_addresses = [rec.eth_address for rec in recipients]
        signed_tx1 = make_contract_call_trx(
            evm_loader,
            session_user,
            transfers_contract,
            "transferNeon(uint256,address[])",
            [10000, recipients_eth_addresses],
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
        emulate_result = neon_api_client.emulate_from_holder(holder_acc)
        assert emulate_result["reverts_before_solana_calls"]
        assert not emulate_result["external_solana_call"]
        assert not emulate_result["reverts_after_solana_calls"]
        assert not emulate_result["is_timestamp_number_used"]

        assert (
            emulate_result["exit_status"] == "revert"
        ), f"The 'exit_status' field is not revert. Result: {emulate_result}"

        resp = evm_loader.execute_transaction_steps_from_account(operator_keypair, treasury_pool, holder_acc, accounts)
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0xD0")
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="contract balance less then needed")

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

        resource_addr = solana_caller.create_resource(session_user, b"q4ww", 8, 1000000000, COUNTER_ID)
        matrix = [[random.randint(1, 100) for _ in range(8)] for _ in range(8)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(resource_addr, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized_instruction = serialize_instruction(COUNTER_ID, instruction)

        signed_tx2 = make_contract_call_trx(
            evm_loader,
            session_user,
            solana_caller.contract,
            "solanaCallInsideActionWithMatrixWithRevert(uint256[][],uint64,bytes)",
            [matrix, 0, serialized_instruction],
        )

        accounts_from_emulation = neon_api_client.get_additional_accounts_by_emulation(
            session_user.eth_address.hex(),
            solana_caller.contract.eth_address.hex(),
            "solanaCallInsideActionWithMatrixWithRevert(uint256[][],uint64,bytes)",
            params=[matrix, 0, serialized_instruction],
        )

        new_holder_acc = evm_loader.create_holder(operator_keypair)
        evm_loader.write_transaction_to_holder_account(signed_tx2, new_holder_acc, operator_keypair)

        for _ in range(1):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                new_holder_acc,
                accounts_from_emulation,
                EVM_STEPS,
                operator_keypair,
            )

        emulate_result = neon_api_client.emulate_from_holder(new_holder_acc)
        assert emulate_result["reverts_after_solana_calls"]
        assert emulate_result["external_solana_call"]
        assert not emulate_result["is_timestamp_number_used"]
        assert not emulate_result["reverts_before_solana_calls"]
        assert (
            emulate_result["exit_status"] == "revert"
        ), f"The 'exit_status' field is not revert. Result: {emulate_result}"

        with pytest.raises(
            RPCException,
            match="Revert after Solana Call is not supported",
        ):
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, new_holder_acc, accounts_from_emulation
            )

    def test_emulate_from_holder_account_timestamp_used_check(
        self,
        operator_keypair,
        sender_with_tokens,
        neon_api_client,
        evm_loader,
        treasury_pool,
        block_timestamp_contract,
    ):
        holder_acc = evm_loader.create_holder(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, block_timestamp_contract, "getBlockTimestamp()"
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        accounts = [
            sender_with_tokens.balance_account_address,
            block_timestamp_contract.solana_address,
        ]

        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )

        emulate_result = neon_api_client.emulate_from_holder(holder_acc)
        assert emulate_result["exit_status"] == "succeed"
        assert emulate_result["is_timestamp_number_used"]
        assert not emulate_result["external_solana_call"]
        assert not emulate_result["reverts_before_solana_calls"]
        assert not emulate_result["reverts_after_solana_calls"]

    def test_emulate_from_holder_account_balance_account_changed(
        self,
        operator_keypair,
        session_user,
        transfers_contract,
        neon_api_client,
        evm_loader,
        treasury_pool,
        holder_acc,
    ):
        amount = 100000
        evm_loader.deposit_neon(operator_keypair, session_user.eth_address, 5 * amount)

        recipients = [
            evm_loader.make_new_user(operator_keypair),
            evm_loader.make_new_user(operator_keypair),
            evm_loader.make_new_user(operator_keypair),
            evm_loader.make_new_user(operator_keypair),
            evm_loader.make_new_user(operator_keypair),
        ]
        recipients_eth_addresses = [rec.eth_address for rec in recipients]

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        signed_tx1 = make_contract_call_trx(
            evm_loader,
            session_user,
            transfers_contract,
            "transferNeon(uint256,address[])",
            [amount, recipients_eth_addresses],
            value=amount * 5,
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
        emulate_result = neon_api_client.emulate_from_holder(holder_acc)
        assert (
            emulate_result["exit_status"] == "succeed"
        ), f"The 'exit_status' field is not succeed. Result: {emulate_result}"
        assert not emulate_result["external_solana_call"]
        assert not emulate_result["is_timestamp_number_used"]
        assert not emulate_result["reverts_before_solana_calls"]
        assert not emulate_result["reverts_after_solana_calls"]

        resp = evm_loader.execute_transaction_steps_from_account(operator_keypair, treasury_pool, holder_acc, accounts)
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_emulate_from_holder_account_before_last_step_executed(
        self,
        evm_loader,
        operator_keypair,
        solana_caller,
        sender_with_tokens,
        neon_api_client,
        new_holder_acc,
        treasury_pool,
    ):
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        resource_addr = solana_caller.create_resource(sender_with_tokens, b"q245w", 8, 1000000000, COUNTER_ID)
        matrix = [[random.randint(1, 100) for _ in range(8)] for _ in range(8)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(resource_addr, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized_instruction = serialize_instruction(COUNTER_ID, instruction)

        signed_tx = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            solana_caller.contract,
            "solanaCallInsideActionWithMatrix(uint256[][],uint64,bytes)",
            [matrix, 0, serialized_instruction],
        )

        accounts_from_emulation = neon_api_client.get_additional_accounts_by_emulation(
            sender_with_tokens.eth_address.hex(),
            solana_caller.contract.eth_address.hex(),
            "solanaCallInsideActionWithMatrix(uint256[][],uint64,bytes)",
            params=[matrix, 0, serialized_instruction],
        )

        evm_loader.write_transaction_to_holder_account(signed_tx, new_holder_acc, operator_keypair)

        for _ in range(1):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                new_holder_acc,
                accounts_from_emulation,
                EVM_STEPS,
                operator_keypair,
            )
        emulate_result_after_1_step = neon_api_client.emulate_from_holder(new_holder_acc)

        for _ in range(14):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                new_holder_acc,
                accounts_from_emulation,
                EVM_STEPS,
                operator_keypair,
            )
        emulate_result = neon_api_client.emulate_from_holder(new_holder_acc)

        assert emulate_result["steps_executed"] == emulate_result_after_1_step["steps_executed"]
        assert emulate_result["iterations"] == emulate_result_after_1_step["iterations"]
        assert emulate_result["external_solana_call"]
        assert emulate_result["exit_status"] == "succeed"
        assert not emulate_result["is_timestamp_number_used"]
        assert not emulate_result["reverts_before_solana_calls"]
        assert not emulate_result["reverts_after_solana_calls"]

        accounts_after_emulation = []
        for item in emulate_result["solana_accounts"]:
            accounts_after_emulation.append(Pubkey.from_string(item["pubkey"]))

        assert sorted(accounts_after_emulation) == sorted(accounts_from_emulation)

        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            new_holder_acc,
            accounts_from_emulation,
            EVM_STEPS,
            operator_keypair,
        )

        check_transaction_logs_have_text(evm_loader, trx=resp, text="exit_status=0x11")

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=new_holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_emulate_from_holder_account_with_small_number_of_steps(
        self, operator_keypair, session_user, rw_lock_contract, neon_api_client, evm_loader, treasury_pool, holder_acc
    ):
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        signed_tx = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [6, 12]
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        accounts = [
            session_user.solana_account_address,
            session_user.balance_account_address,
            rw_lock_contract.solana_address,
        ]

        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )

        emulate_result = neon_api_client.emulate_from_holder(holder_acc, max_steps_to_execute=5)
        assert (
            emulate_result["exit_status"] == "revert"
        ), f"The 'exit_status' field is not revert. Result: {emulate_result}"

        resp = evm_loader.execute_transaction_steps_from_account(operator_keypair, treasury_pool, holder_acc, accounts)
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x12")

    @pytest.mark.parametrize("write_tx_to_holder", [True, False])
    def test_emulate_from_holder_account_with_wrong_holder_account_tag(
        self,
        operator_keypair,
        session_user,
        rw_lock_contract,
        neon_api_client,
        evm_loader,
        write_tx_to_holder,
    ):
        holder_acc = evm_loader.create_holder(operator_keypair)
        if write_tx_to_holder:
            signed_tx = make_contract_call_trx(
                evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [6, 12]
            )
            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        emulate_result = neon_api_client.emulate_from_holder(holder_acc)
        assert emulate_result["result"] == "error"
        assert "invalid status" in emulate_result["error"]
