import pytest
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.constants import TAG_FINALIZED_STATE
from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import (
    check_holder_account_tag,
    check_transaction_logs_have_text,
)
from utils.evm_loader import EVM_STEPS
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT


class TestBlockNumberAndTimestamp:
    @pytest.fixture(scope="session", params=["BlockTimestamp", "BlockNumber"])
    def block_contract(self, request, evm_loader, operator_keypair, sender_with_tokens, neon_rpc_client, treasury_pool):
        name = request.param
        return evm_loader.deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "common/Block.sol",
            neon_rpc_client,
            treasury_pool,
            contract_name=name,
            version="0.8.10",
        )

    def test_trx_steps_with_number_timestamp(
        self,
        block_contract,
        operator_keypair,
        treasury_pool,
        neon_rpc_client,
        evm_loader,
        sender_with_tokens,
        holder_acc,
    ):
        """
        This test repeats the proxy's logic of reemulation with account info overrides and block overrides.
        """
        params = [4, 123, 20]
        func_signature = "addDataToMapping(uint256,uint256,uint256)"

        emulate_result = neon_rpc_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(), block_contract.eth_address.hex(), func_signature, params=params
        )
        # Accounts to execute the first iteration.
        initial_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, block_contract, func_signature, params=params
        )

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        def get_account_override(eth_account):
            sender_address = eth_account.eth_address.hex()
            sender_account_info = neon_rpc_client.get_balance(sender_address)[0]

            return {
                sender_address: {"nonce": sender_account_info["trx_count"], "balance": sender_account_info["balance"]}
            }

        def get_block_params():
            block_params = neon_rpc_client.get_holder(holder_acc)["block_params"]
            block_timestamp, block_number = int(block_params[0], 16), int(block_params[1], 16)

            return {"number": block_number, "time": block_timestamp}

        def make_trace_config(block_params, overrides):
            return {"blockOverrides": block_params, "stateOverrides": overrides}

        # State of the sender account should be fetched before the first iteration.
        sender_overrides = get_account_override(sender_with_tokens)
        evm_loader.send_transaction_step_from_account(
            operator_keypair,
            operator_balance_pubkey,
            treasury_pool,
            holder_acc,
            initial_accounts,
            EVM_STEPS,
            operator_keypair,
        )

        # Fetch block params after the first iteration as stored in the holder.
        block_params = get_block_params()

        # Reemulate after the first iteration
        emulate_result = neon_rpc_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(),
            block_contract.eth_address.hex(),
            func_signature,
            params=params,
            trace_config=make_trace_config(block_params, sender_overrides),
        )

        # Fetch new account list that depends on the re-emulation.
        new_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        evm_loader.execute_transaction_steps_from_account(operator_keypair, treasury_pool, holder_acc, new_accounts)

        check_holder_account_tag(
            solana_client=evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

    def test_block_number_timestamp_reset_for_changed_revision(
        self,
        block_contract,
        operator_keypair,
        evm_loader,
        sender_with_tokens,
        neon_rpc_client,
        treasury_pool,
        holder_acc,
        second_holder_acc,
    ):
        """Check that all steps with timestamp is restarted
        with new value of timestamp/timeblock after changing revisions
        """
        func_signature = "accrueInterest()"

        emulate_result = neon_rpc_client.emulate_contract_call(
            sender_with_tokens.eth_address.hex(), block_contract.eth_address.hex(), func_signature
        )
        emulated_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        signed_tx = make_contract_call_trx(evm_loader, sender_with_tokens, block_contract, func_signature)

        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)

        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        for i in range(2):
            evm_loader.send_transaction_step_from_account(
                operator_keypair,
                operator_balance_pubkey,
                treasury_pool,
                holder_acc,
                emulated_accounts,
                EVM_STEPS,
                operator_keypair,
            )

        # run second transaction
        signed_tx2 = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            block_contract,
            func_signature,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx2, second_holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, second_holder_acc, emulated_accounts
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder_acc, emulated_accounts, check_invalid_revision=True
        )

        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")
