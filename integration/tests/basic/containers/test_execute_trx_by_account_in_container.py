import random

import allure
import pytest
from solders.pubkey import Pubkey

from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from utils.accounts import EthAccounts
from utils.consts import COUNTER_ID
from utils.helpers import serialize_instruction, decode_function_signature, wait_condition
from utils.instructions import make_increment_counter
from utils.scheduled_trx import ScheduledTrxEstimateRequest, CreateTreeAccMultipleData, ScheduledTransaction
from utils.web3client import NeonChainWeb3Client


@pytest.mark.only_stands
@allure.feature("Containers")
@allure.story("Send trxs by accounts in containers")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestContainerizedAccounts:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_call_contract_in_container_by_acc_in_container(
        self, distributor_contract, evm_loader, treasury_pool, operator
    ):
        acc_in_container = self.accounts[6]
        balance_before = self.web3_client.get_balance(acc_in_container.address)

        sender = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender)
        instruction_tx = distributor_contract.functions.set_address(
            "alice", bytes.fromhex(acc_in_container.address[2:])
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

        container_address = evm_loader.ether2program(distributor_contract.address[2:])
        evm_loader.assemble_container(
            operator=operator.operator_keypairs[0],
            treasury=treasury_pool,
            container_address=container_address,
            accounts=[evm_loader.ether2balance(acc_in_container.address[2:])],
        )
        amount = 300
        tx = self.web3_client.make_raw_tx(sender, amount=amount)
        instruction_tx = distributor_contract.functions.distribute_value().build_transaction(tx)

        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"
        balance_after = self.web3_client.get_balance(acc_in_container.address)
        assert balance_after == balance_before + amount, "Balance should be updated correctly"

        # sign trx by account added to container
        tx = self.web3_client.make_raw_tx(acc_in_container, amount=amount)
        instruction_tx = distributor_contract.functions.distribute_value().build_transaction(tx)

        receipt = self.web3_client.send_transaction(acc_in_container, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

    def test_send_token_to_empty_to_field_by_acc_in_container(self, account_in_container):
        sender_account = account_in_container
        sender_balance = self.web3_client.get_balance(sender_account)

        self.web3_client.send_neon(sender_account, to=None, amount=1)
        assert sender_balance > self.web3_client.get_balance(sender_account)

    def test_solana_call_before_iterative_actions_by_acc_in_container(
        self,
        counter_resource_address: Pubkey,
        call_solana_caller,
        account_in_container,
    ):
        sender = account_in_container
        matrix_length = 15
        matrix = [[random.randint(1, 100) for _ in range(matrix_length)] for _ in range(matrix_length)]

        instruction = make_increment_counter(counter_resource_address)
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)

        instruction_tx = call_solana_caller.functions.solanaCallBeforeActionWithMatrix(
            matrix, 0, serialized
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 0, resp

    def test_call_scheduled_trx_by_neon_user_in_container(
        self, neon_user_func_scope, alt_contract_containerized, treasury_pool, web3_client_sol, evm_loader, operator
    ):
        func_name = "fill(uint256)"
        data = decode_function_signature(func_name, [14])

        def send_scheduled_trx(balance_acc_in_container):
            trx_estimate_obj = ScheduledTrxEstimateRequest(
                neon_user_func_scope.checksum_address, alt_contract_containerized.address, data
            )

            estimate_result = web3_client_sol.estimate_scheduled(
                neon_user_func_scope.solana_account.pubkey(), [trx_estimate_obj]
            )
            trx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

            tree_acc_data = CreateTreeAccMultipleData(
                nonce=estimate_result["nonce"],
                max_fee_per_gas=estimate_result["maxFeePerGas"],
                max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
            )

            tree_acc_data.add_trx(trx, 0xFFFF, 0)
            tree_account = evm_loader.create_tree_account_multiple(
                neon_user_func_scope,
                treasury_pool,
                tree_acc_data.data,
                payer_nonce=int(estimate_result["nonce"], 16),
                balance_acc_in_container=balance_acc_in_container,
            )
            web3_client_sol.send_scheduled_transaction(trx)
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=120)
            wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

        send_scheduled_trx(balance_acc_in_container=None)
        container_address = evm_loader.ether2program(alt_contract_containerized.address[2:])
        evm_loader.assemble_container(
            operator.operator_keypairs[0],
            treasury_pool,
            container_address,
            [evm_loader.ether2balance(neon_user_func_scope.neon_address, web3_client_sol.chain_id)],
        )
        send_scheduled_trx(balance_acc_in_container=container_address)

    def test_assemble_container_after_creating_tree_acc_before_sending_trx(
        self, neon_user_func_scope, alt_contract_containerized, treasury_pool, web3_client_sol, evm_loader, operator
    ):
        func_name = "fill(uint256)"
        data = decode_function_signature(func_name, [14])
        trx_estimate_obj = ScheduledTrxEstimateRequest(
            neon_user_func_scope.checksum_address, alt_contract_containerized.address, data
        )

        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user_func_scope.solana_account.pubkey(), [trx_estimate_obj]
        )
        trx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trx, 0xFFFF, 0)
        tree_account = evm_loader.create_tree_account_multiple(
            neon_user_func_scope, treasury_pool, tree_acc_data.data, payer_nonce=int(estimate_result["nonce"], 16)
        )

        evm_loader.assemble_container(
            operator.operator_keypairs[0],
            treasury_pool,
            evm_loader.ether2program(alt_contract_containerized.address[2:]),
            [evm_loader.ether2balance(neon_user_func_scope.neon_address, web3_client_sol.chain_id)],
        )
        web3_client_sol.send_scheduled_transaction(trx)
        check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=120)
        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)
