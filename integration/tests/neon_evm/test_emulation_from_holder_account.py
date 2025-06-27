import pytest

from solders.pubkey import Pubkey
from utils.evm_loader import EVM_STEPS
from utils.consts import REMAPPING_ZEPPELIN
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
    def test_emulate_from_holder_account_contract_function_call(
        self,
        operator_keypair,
        session_user,
        rw_lock_contract,
        neon_api_client,
        evm_loader,
        treasury_pool,
        holder_acc,
        sol_client,
    ):
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        signed_tx = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [2, 2]
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
        assert int(emulate_result["result"]) == 4

        resp = evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            accounts,
            EVM_STEPS,
            operator_keypair,
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x12")

        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_emulate_from_holder_account_contract_deploy(
        self, operator_keypair, sender_with_tokens, neon_api_client, evm_loader, treasury_pool, holder_acc, sol_client
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
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_emulate_from_holder_account_failed_trx(
        self,
        operator_keypair,
        session_user,
        neon_api_client,
        evm_loader,
        treasury_pool,
        holder_acc,
        sol_client,
        transfers_contract,
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
        assert (
            emulate_result["exit_status"] == "revert"
        ), f"The 'exit_status' field is not revert. Result: {emulate_result}"

        resp = evm_loader.execute_transaction_steps_from_account(operator_keypair, treasury_pool, holder_acc, accounts)
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0xD0")
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="contract balance less then needed")

        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_emulate_from_holder_account_balance_account_changed(
        self,
        operator_keypair,
        session_user,
        transfers_contract,
        neon_api_client,
        evm_loader,
        treasury_pool,
        holder_acc,
        sol_client,
    ):
        amount = 100000
        evm_loader.deposit_neon(operator_keypair, session_user.eth_address, 3 * amount)

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
        emulate_result = neon_api_client.emulate_from_holder(holder_acc)
        assert (
            emulate_result["exit_status"] == "succeed"
        ), f"The 'exit_status' field is not succeed. Result: {emulate_result}"

        resp = evm_loader.execute_transaction_steps_from_account(operator_keypair, treasury_pool, holder_acc, accounts)
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
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
