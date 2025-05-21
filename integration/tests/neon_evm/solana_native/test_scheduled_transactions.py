import eth_abi
import pytest
import solana
from eth_utils import abi, to_int
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.assert_messages import InstructionAsserts
from integration.tests.neon_evm.utils.neon_api_client import NeonApiClient
from utils.consts import LAMPORT_PER_SOL
from utils.helpers import wait_condition
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction


class TestScheduledTrx:
    # This tests can be run only with environment WITHOUT proxy service
    def test_execute_scheduled_trx_from_account(
        self, evm_loader, neon_user: NeonUser, treasury_pool, basic_contract, neon_api_client, operator_keypair
    ):
        holder_acc = evm_loader.create_holder(operator_keypair)
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            0,
            target=basic_contract.eth_address,
            value=0,
            call_data=data,
            chain_id=evm_loader.sol_chain_id,
        )
        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())
        transaction_tree_data = neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce)
        assert transaction_tree_data.get_transaction_count() == 1

        evm_loader.write_transaction_to_holder_account(tx.encode(), holder_acc, operator_keypair)
        additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(evm_loader.sol_chain_id)]
        evm_loader.execute_scheduled_trx_from_account(
            0, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts, compute_unit_price=3929
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)
        evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_account)
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).get_transaction_count() == 0

    def test_execute_scheduled_trx_from_instruction(
        self,
        evm_loader,
        neon_user: NeonUser,
        treasury_pool,
        basic_contract,
        neon_api_client: NeonApiClient,
        operator_keypair,
    ):
        holder_acc = evm_loader.create_holder(operator_keypair)
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            0,
            target=basic_contract.eth_address,
            value=0,
            call_data=data,
            chain_id=evm_loader.sol_chain_id,
        )

        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).get_transaction_count() == 1

        additional_accounts = [
            basic_contract.solana_address,
            neon_user.get_balance_account(evm_loader.sol_chain_id),
        ]
        evm_loader.execute_scheduled_trx_from_instruction(
            tx, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )

        data = abi.function_signature_to_4byte_selector("getNumber()")
        result = neon_api_client.emulate(
            neon_user.neon_address.hex(), contract=basic_contract.eth_address.hex(), data=data
        )
        assert to_int(hexstr=result["result"]) == contract_data

        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)
        evm_loader.destroy_tree_account(neon_user, treasury_pool, tree_account)
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).get_transaction_count() == 0

    def test_scheduled_trx_wrong_index(
        self, evm_loader, neon_user: NeonUser, treasury_pool, basic_contract, operator_keypair, holder_acc
    ):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
        data = abi.function_signature_to_4byte_selector("getNumber()")
        index = 1
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            index,
            target=basic_contract.eth_address,
            value=0,
            chain_id=evm_loader.sol_chain_id,
            call_data=data,
        )

        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.TRANSACTION_TREE_INVALID_DATA):
            evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())

    def test_send_sol_with_zero_fee(
        self,
        evm_loader,
        neon_user: NeonUser,
        treasury_pool,
        neon_api_client: NeonApiClient,
        operator_keypair,
        sender_with_wsol,
    ):
        contract = evm_loader.deploy_contract(
            operator_keypair,
            sender_with_wsol,
            "transfers",
            neon_api_client,
            treasury_pool,
            chain_id=evm_loader.sol_chain_id,
        )

        nonce = evm_loader.get_neon_nonce(account=neon_user.neon_address, chain_id=evm_loader.sol_chain_id)
        data = abi.function_signature_to_4byte_selector("donate1000()")
        amount = 10000
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            0,
            target=contract.eth_address,
            value=amount,
            call_data=data,
            gas_limit=25000,
            max_fee_per_gas=0,
            max_priority_fee_per_gas=0,
            chain_id=evm_loader.sol_chain_id,
        )
        with pytest.raises(solana.rpc.core.RPCException, match=InstructionAsserts.TRANSACTION_TREE_NO_FEE):
            evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())

    def test_out_of_gas(
        self,
        evm_loader,
        neon_user: NeonUser,
        treasury_pool,
        operator_keypair,
        sender_with_wsol,
        neon_api_client,
    ):
        contract = evm_loader.deploy_contract(
            operator_keypair,
            sender_with_wsol,
            "transfers",
            neon_api_client,
            treasury_pool,
            chain_id=evm_loader.sol_chain_id,
        )
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, evm_loader.sol_chain_id)
        data = abi.function_signature_to_4byte_selector("donate1000()")
        amount = 10000
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            0,
            target=contract.eth_address,
            value=amount,
            call_data=data,
            gas_limit=20000,
            chain_id=evm_loader.sol_chain_id,
        )

        with pytest.raises(solana.rpc.core.RPCException, match="transaction requires at least 25'000 gas limit"):
            evm_loader.create_tree_account(neon_user, treasury_pool, tx.encode())

    def test_send_sol_with_priority_fee(
        self,
        evm_loader,
        neon_user: NeonUser,
        treasury_pool_new,
        neon_api_client,
        second_operator_keypair,
        sender_with_wsol,
    ):
        contract = evm_loader.deploy_contract(
            second_operator_keypair,
            sender_with_wsol,
            "transfers",
            neon_api_client,
            treasury_pool_new,
            chain_id=evm_loader.sol_chain_id,
        )

        evm_loader.deposit_wrapped_sol_from_solana_to_neon(
            neon_user.solana_account,
            "0x" + neon_user.neon_address.hex(),
            int(1 * LAMPORT_PER_SOL),
        )
        holder_acc = evm_loader.create_holder(second_operator_keypair)
        nonce = evm_loader.get_neon_nonce(account=neon_user.neon_address, chain_id=evm_loader.sol_chain_id)
        data = abi.function_signature_to_4byte_selector("donate1000()")
        amount = 10000
        tx = ScheduledTransaction(
            neon_user.neon_address,
            None,
            nonce,
            0,
            target=contract.eth_address,
            value=amount,
            call_data=data,
            chain_id=evm_loader.sol_chain_id,
        )
        operator_balance_before = evm_loader.get_operator_neon_balance(second_operator_keypair, evm_loader.sol_chain_id)
        user_balance_before = evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id)
        treasury_balance_before = evm_loader.get_solana_balance(treasury_pool_new.account)

        tree_account = evm_loader.create_tree_account(neon_user, treasury_pool_new, tx.encode())

        wait_condition(lambda: evm_loader.get_solana_balance(treasury_pool_new.account) < treasury_balance_before)
        wait_condition(lambda: evm_loader.get_solana_balance(tree_account) > 0)
        wait_condition(
            lambda: evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id) < user_balance_before
        )

        user_balance_after = evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id)
        treasury_balance_after = evm_loader.get_solana_balance(treasury_pool_new.account)
        user_balance_diff = user_balance_before - user_balance_after
        treasury_balance_diff = treasury_balance_before - treasury_balance_after

        assert treasury_balance_diff > 0
        assert user_balance_diff > 0

        emulate_result = neon_api_client.emulate(
            neon_user.neon_address.hex(),
            contract.eth_address.hex(),
            data,
            chain_id=evm_loader.sol_chain_id,
            value=hex(amount),
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        evm_loader.write_transaction_to_holder_account(tx.encode(), holder_acc, second_operator_keypair)
        evm_loader.execute_scheduled_trx_from_account(
            0,
            second_operator_keypair,
            holder_acc,
            tree_account,
            treasury_pool_new,
            additional_accounts,
            compute_unit_price=3929,
        )
        evm_loader.finish_scheduled_trx(second_operator_keypair, tree_account, holder_acc)
        user_balance_before_destroy = evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id)

        evm_loader.destroy_tree_account(neon_user, treasury_pool_new, tree_account)
        user_balance_after_destroy = evm_loader.get_neon_balance(neon_user.neon_address, evm_loader.sol_chain_id)

        assert user_balance_after_destroy > user_balance_before_destroy
        operator_balance_after = evm_loader.get_operator_neon_balance(
            operator=second_operator_keypair, chain_id=evm_loader.sol_chain_id
        )
        assert operator_balance_after > operator_balance_before
