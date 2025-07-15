import pytest
from solana.rpc.core import RPCException

from utils.evm_loader import EVM_STEPS
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from .utils.constants import TAG_FINALIZED_STATE
from .utils.ethereum import make_contract_call_trx
from .utils.transaction_checks import check_holder_account_tag


class TestCancelTrx:
    def test_cancel_trx(
        self, operator_keypair, rw_lock_contract, session_user, treasury_pool, evm_loader, neon_api_client, holder_acc
    ):
        """EVM can cancel transaction and finalize storage account"""
        signed_tx = make_contract_call_trx(
            evm_loader, session_user, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
        )
        additional_accounts = neon_api_client.get_additional_accounts_by_emulation(
            session_user.eth_address.hex(), rw_lock_contract.eth_address.hex(), "unchange_storage(uint8,uint8)", [1, 1]
        )

        user_nonce_before_first_step = evm_loader.get_neon_nonce(session_user.eth_address)
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)

        receipt = evm_loader.send_transaction_step_from_instruction(
            operator_keypair,
            operator_balance,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
            1,
            operator_keypair,
        )

        assert receipt.value.transaction.meta.err is None

        user_nonce_after_first_step = evm_loader.get_neon_nonce(session_user.eth_address)
        assert user_nonce_before_first_step + 1 == user_nonce_after_first_step
        evm_loader.send_cancel_transaction(operator_keypair, holder_acc, additional_accounts, signed_tx.hash)
        check_holder_account_tag(
            evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )
        assert user_nonce_after_first_step == evm_loader.get_neon_nonce(session_user.eth_address)

    @pytest.mark.parametrize("gas_limit", [10000, 15000, 16000])
    def test_cancel_after_out_of_gas(
        self,
        operator_keypair,
        rw_lock_contract,
        sender_with_tokens,
        treasury_pool,
        evm_loader,
        neon_api_client,
        gas_limit,
        holder_acc,
    ):
        """If after some iterations there is not enough neon to cancel, the cancel
        instruction can still be executed, and as many neons as possible will be charged
        (but not exceeding the gas limit)."""
        signed_tx = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            rw_lock_contract,
            "unchange_storage(uint8,uint8)",
            [1, 1],
            gas=gas_limit,
            gas_price=1,
        )

        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
        user_neon_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        additional_accounts = [
            rw_lock_contract.solana_address,
            rw_lock_contract.balance_account_address,
            sender_with_tokens.balance_account_address,
        ]
        # first successful iteration
        receipt = evm_loader.send_transaction_step_from_instruction(
            operator_keypair,
            operator_balance,
            treasury_pool,
            holder_acc,
            signed_tx,
            additional_accounts,
            1,
            operator_keypair,
        )

        assert receipt.value.transaction.meta.err is None
        if gas_limit - 5000 < 5000:
            with pytest.raises(RPCException, match="Out of Gas"):
                evm_loader.send_transaction_step_from_instruction(
                    operator_keypair,
                    operator_balance,
                    treasury_pool,
                    holder_acc,
                    signed_tx,
                    additional_accounts,
                    EVM_STEPS,
                    operator_keypair,
                )

        evm_loader.send_cancel_transaction(operator_keypair, holder_acc, additional_accounts, signed_tx.hash)
        check_holder_account_tag(
            evm_loader,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

        user_neon_balance_after = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        if gas_limit - 5000 <= 10000:
            assert user_neon_balance_after == user_neon_balance_before - gas_limit
        else:
            assert user_neon_balance_after == user_neon_balance_before - 16000
