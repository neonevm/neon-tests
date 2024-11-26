import pytest
import solana
from solana.transaction import Transaction

from utils.evm_loader import EVM_STEPS
from utils.instructions import make_Cancel
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from .utils.constants import TAG_FINALIZED_STATE
from .utils.contract import make_contract_call_trx
from .utils.storage import create_holder
from .utils.transaction_checks import check_holder_account_tag


class TestCancelTrx:
    def test_cancel_trx(self, operator_keypair, rw_lock_contract, user_account, treasury_pool, evm_loader):
        """EVM can cancel transaction and finalize storage account"""
        signed_tx = make_contract_call_trx(
            evm_loader, user_account, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1]
        )

        storage_account = create_holder(operator_keypair, evm_loader)
        user_nonce_before_first_step = evm_loader.get_neon_nonce(user_account.eth_address)
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)

        receipt = evm_loader.send_transaction_step_from_instruction(
            operator_keypair,
            operator_balance,
            treasury_pool,
            storage_account,
            signed_tx,
            [
                rw_lock_contract.solana_address,
                rw_lock_contract.balance_account_address,
                user_account.balance_account_address,
            ],
            1,
            operator_keypair,
        )

        assert receipt.value.transaction.meta.err is None

        user_nonce_after_first_step = evm_loader.get_neon_nonce(user_account.eth_address)
        assert user_nonce_before_first_step + 1 == user_nonce_after_first_step
        trx = Transaction()
        trx.add(
            make_Cancel(
                evm_loader.loader_id,
                storage_account,
                operator_keypair,
                operator_balance,
                signed_tx.hash,
                [
                    rw_lock_contract.solana_address,
                    rw_lock_contract.balance_account_address,
                    user_account.balance_account_address,
                ],
            )
        )
        evm_loader.send_tx(trx, operator_keypair)
        check_holder_account_tag(storage_account, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        assert user_nonce_after_first_step == evm_loader.get_neon_nonce(user_account.eth_address)

    @pytest.mark.parametrize("gas_limit", [6000, 5000, 15000, 16000])
    def test_cancel_after_out_of_gas(
        self, operator_keypair, rw_lock_contract, sender_with_tokens, treasury_pool, evm_loader, neon_api_client, gas_limit
    ):
        """If after some iterations there is not enough neon to cancel, the cancel
        instruction can still be executed, and as many neons as possible will be charged
        (but not exceeding the gas limit)."""
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, rw_lock_contract,
            "unchange_storage(uint8,uint8)", [1, 1], gas=gas_limit, gas_price=1
        )

        storage_account = create_holder(operator_keypair, evm_loader)
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
        user_neon_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        # first successful iteration
        receipt = evm_loader.send_transaction_step_from_instruction(
            operator_keypair,
            operator_balance,
            treasury_pool,
            storage_account,
            signed_tx,
            [
                rw_lock_contract.solana_address,
                rw_lock_contract.balance_account_address,
                sender_with_tokens.balance_account_address,
            ],
            1,
            operator_keypair,
        )
        assert receipt.value.transaction.meta.err is None
        if gas_limit - 5000 < 5000:
            with pytest.raises(solana.rpc.core.RPCException, match="Out of Gas"):
                evm_loader.send_transaction_step_from_instruction(
                    operator_keypair,
                    operator_balance,
                    treasury_pool,
                    storage_account,
                    signed_tx,
                    [
                        rw_lock_contract.solana_address,
                        rw_lock_contract.balance_account_address,
                        sender_with_tokens.balance_account_address,
                    ],
                    EVM_STEPS,
                    operator_keypair,
                )

        trx = Transaction()
        trx.add(
            make_Cancel(
                evm_loader.loader_id,
                storage_account,
                operator_keypair,
                operator_balance,
                signed_tx.hash,
                [
                    rw_lock_contract.solana_address,
                    rw_lock_contract.balance_account_address,
                    sender_with_tokens.balance_account_address,
                ],
            )
        )
        evm_loader.send_tx(trx, operator_keypair)
        check_holder_account_tag(storage_account, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        user_neon_balance_after = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        if gas_limit - 5000 <= 10000:
            assert user_neon_balance_after == user_neon_balance_before - gas_limit
        else:
            assert user_neon_balance_after == user_neon_balance_before - 15000
