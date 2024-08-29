import pytest
import solana

from integration.tests.neon_evm.utils.constants import TAG_FINALIZED_STATE
from integration.tests.neon_evm.utils.contract import make_contract_call_trx, make_deployment_transaction
from integration.tests.neon_evm.utils.ethereum import create_contract_address, make_eth_transaction
from integration.tests.neon_evm.utils.transaction_checks import (
    check_holder_account_tag,
    check_transaction_logs_have_text,
)
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from utils.types import Caller


class TestEIP1559Transactions:
    def test_contract_interaction_iterative_transactions(
            self,
            operator_keypair,
            holder_acc,
            treasury_pool,
            sender_with_tokens,
            evm_loader,
            calculator_contract,
            calculator_caller_contract,
    ):
        signed_tx = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            calculator_caller_contract,
            "callCalculator()",
            max_fee_per_gas=10000,
            max_priority_fee_per_gas=10,
            trx_type=2,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair,
            treasury_pool,
            holder_acc,
            [
                calculator_caller_contract.solana_address,
                calculator_contract.solana_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
            compute_unit_price=3929,
        )

        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_transaction_logs_have_text(resp, "exit_status=0x12")

    def test_contract_deploy_iterative_transaction(
            self, operator_keypair, holder_acc, treasury_pool, sender_with_tokens, evm_loader
    ):
        contract_filename = "hello_world"
        contract = create_contract_address(sender_with_tokens, evm_loader)

        signed_tx = make_deployment_transaction(
            evm_loader, sender_with_tokens, contract_filename, max_fee_per_gas=10000, max_priority_fee_per_gas=10
        )

        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair,
            treasury_pool,
            holder_acc,
            [
                contract.solana_address,
                contract.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
            compute_unit_price=5000,
        )

        check_holder_account_tag(holder_acc, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        check_transaction_logs_have_text(resp, "exit_status=0x12")

    def test_max_fee_less_then_max_priority_fee(
            self,
            operator_keypair,
            holder_acc,
            treasury_pool,
            sender_with_tokens,
            evm_loader,
            calculator_contract,
            calculator_caller_contract,
    ):
        signed_tx = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            calculator_caller_contract,
            "callCalculator()",
            max_fee_per_gas=10,
            max_priority_fee_per_gas=1000,
            trx_type=2,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        with pytest.raises(solana.rpc.core.RPCException, match="max_fee_per_gas < max_priority_fee_per_gas"):
            evm_loader.execute_transaction_steps_from_account(
                operator_keypair,
                treasury_pool,
                holder_acc,
                [
                    calculator_caller_contract.solana_address,
                    calculator_contract.solana_address,
                    sender_with_tokens.solana_account_address,
                    sender_with_tokens.balance_account_address,
                ],
                compute_unit_price=3929,
            )

    def test_simple_transfer_non_iterative_transaction(
            self,
            operator_keypair,
            treasury_pool,
            sender_with_tokens: Caller,
            session_user: Caller,
            evm_loader,
            holder_acc
    ):
        amount = 10
        max_fee_per_gas = 50000
        max_priority_fee_per_gas = 100

        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        recipient_balance_before = evm_loader.get_neon_balance(session_user.eth_address)

        signed_tx = make_eth_transaction(
            evm_loader,
            session_user.eth_address,
            None,
            sender_with_tokens,
            amount,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas=10000,
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
            compute_unit_price=5000,
        )

        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        recipient_balance_after = evm_loader.get_neon_balance(session_user.eth_address)

        additional_fee = max_priority_fee_per_gas * 5000 * 1
        assert sender_balance_before - amount - sender_balance_after > additional_fee
        assert recipient_balance_before + amount == recipient_balance_after
        check_transaction_logs_have_text(resp, "exit_status=0x11")
