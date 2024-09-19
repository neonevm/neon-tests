from .utils.contract import make_deployment_transaction
from .utils.ethereum import make_eth_transaction, create_contract_address
from .utils.storage import create_holder


class TestTransactionStepFromAccount:
    def test_simple_transfer_transaction(
        self, operator_keypair, treasury_pool, evm_loader, sender_with_tokens, session_user, holder_acc
    ):
        amount = 10

        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, amount)
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        resp_from_acc = evm_loader.execute_transaction_steps_from_account(
            operator_keypair,
            treasury_pool,
            holder_acc,
            [
                session_user.solana_account_address,
                session_user.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, amount)
        resp_from_inst = evm_loader.execute_transaction_steps_from_instruction(
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
        assert resp_from_acc.value.transaction.meta.fee == resp_from_inst.value.transaction.meta.fee
        assert (
            resp_from_acc.value.transaction.meta.inner_instructions
            == resp_from_inst.value.transaction.meta.inner_instructions
        )
        for i in range(len(resp_from_acc.value.transaction.meta.post_balances)):
            assert (
                resp_from_acc.value.transaction.meta.post_balances[i]
                - resp_from_acc.value.transaction.meta.pre_balances[i]
                == resp_from_inst.value.transaction.meta.post_balances[i]
                - resp_from_inst.value.transaction.meta.pre_balances[i]
            )

    def test_deploy_contract(self, operator_keypair, holder_acc, treasury_pool, evm_loader, sender_with_tokens):
        contract_filename = "small"
        contract = create_contract_address(sender_with_tokens, evm_loader)

        signed_tx = make_deployment_transaction(evm_loader, sender_with_tokens, contract_filename)
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        resp_from_acc = evm_loader.execute_transaction_steps_from_account(
            operator_keypair,
            treasury_pool,
            holder_acc,
            [
                contract.solana_address,
                contract.balance_account_address,
                sender_with_tokens.solana_account_address,
                sender_with_tokens.balance_account_address,
            ],
        )
        signed_tx = make_deployment_transaction(evm_loader, sender_with_tokens, contract_filename)
        holder_acc = create_holder(operator_keypair, evm_loader)
        contract = create_contract_address(sender_with_tokens, evm_loader)

        resp_from_inst = evm_loader.execute_transaction_steps_from_instruction(
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
        assert resp_from_acc.value.transaction.meta.fee == resp_from_inst.value.transaction.meta.fee
        assert len(resp_from_acc.value.transaction.meta.inner_instructions) == len(
            resp_from_inst.value.transaction.meta.inner_instructions
        )
        assert len(resp_from_acc.value.transaction.transaction.message.account_keys) == len(
            resp_from_acc.value.transaction.transaction.message.account_keys
        )
