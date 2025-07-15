from integration.tests.neon_evm.utils.constants import TAG_HOLDER
from integration.tests.neon_evm.utils.ethereum import (
    make_eth_transaction,
    create_contract_address,
    make_deployment_transaction,
)
from integration.tests.neon_evm.utils.transaction_checks import (
    check_transaction_logs_have_text,
    check_holder_account_tag,
)
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from utils.types import Caller


class TestExecuteTrxFromAccount:
    def test_simple_transfer_transaction(
        self,
        operator_keypair,
        treasury_pool,
        sender_with_tokens: Caller,
        session_user: Caller,
        holder_acc,
        evm_loader,
        sol_client,
    ):
        amount = 10
        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        recipient_balance_before = evm_loader.get_neon_balance(session_user.eth_address)
        signed_tx = make_eth_transaction(
            evm_loader, session_user.eth_address, None, sender_with_tokens, amount, chain_id=None
        )

        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        resp = evm_loader.execute_trx_from_account(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
            operator_keypair,
        )
        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        recipient_balance_after = evm_loader.get_neon_balance(session_user.eth_address)
        assert sender_balance_before - amount == sender_balance_after
        assert recipient_balance_before + amount == recipient_balance_after
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x11")

    def test_deploy_contract(
        self,
        operator_keypair,
        sol_client,
        holder_acc,
        treasury_pool,
        evm_loader,
        sender_with_tokens,
        neon_api_client,
    ):
        contract = create_contract_address(sender_with_tokens, evm_loader)

        signed_tx = make_deployment_transaction(evm_loader, sender_with_tokens, "hello_world")
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        resp = evm_loader.execute_trx_from_account(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            [
                contract.solana_address,
                contract.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
            operator_keypair,
        )
        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_HOLDER,
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x12")
