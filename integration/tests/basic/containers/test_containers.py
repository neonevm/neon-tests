import allure
import pytest
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair

from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from utils.accounts import EthAccounts
from utils.consts import AccountType
from utils.helpers import decode_function_signature, wait_condition, gen_hash_of_block
from utils.scheduled_trx import ScheduledTrxEstimateRequest, CreateTreeAccMultipleData, ScheduledTransaction
from utils.solana_data_for_neon_trx_helper import (
    get_sol_account_list_by_neon_trx,
    get_accounts_for_container_by_emulation,
)
from utils.solana_interoperability_helper import prepare_transfer_spl_data
from utils.web3client import NeonChainWeb3Client


@allure.feature("Containers")
@allure.story("Send trxs with containers")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestContainers:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_change_data_accounts_in_container(self, rw_lock_contract_containerized):
        sender = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender)
        instruction_tx = rw_lock_contract_containerized.functions.update_storage(20).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

    def test_big_count_of_accounts_in_container(
        self, accounts, alt_contract_containerized, evm_loader, treasury_pool, operator
    ):
        container_address = evm_loader.ether2program(alt_contract_containerized.address[2:])
        sender = accounts[3]
        for n in [50, 75, 100, 125, 150]:
            tx = self.web3_client.make_raw_tx(sender)
            instruction_tx = alt_contract_containerized.functions.fill(n).build_transaction(tx)
            sol_accounts = get_accounts_for_container_by_emulation(
                self.web3_client, evm_loader, instruction_tx, sender, container_address
            )
            self.web3_client.send_transaction(sender, instruction_tx)
            evm_loader.assemble_container(operator.operator_keypairs[0], treasury_pool, container_address, sol_accounts)

        tx = self.web3_client.make_raw_tx(sender)
        instruction_tx = alt_contract_containerized.functions.fill(175).build_transaction(tx)
        self.web3_client.send_transaction(sender, instruction_tx)

    def test_scheduled_trx_with_container(
        self, neon_user, alt_contract_containerized, treasury_pool, web3_client_sol, evm_loader, operator
    ):
        func_name = "fill(uint256)"
        data1 = decode_function_signature(func_name, [14])
        data2 = decode_function_signature(func_name, [30])
        data3 = decode_function_signature(func_name, [20])
        data4 = decode_function_signature(func_name, [20])

        trx_estimate_obj_list = []
        for data in [data1, data2, data3]:
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(
                    neon_user.checksum_address, alt_contract_containerized.address, data, child_transaction=hex(3)
                )
            )
        trx_estimate_obj_list.append(
            ScheduledTrxEstimateRequest(
                neon_user.checksum_address, alt_contract_containerized.address, data4, child_transaction="0xFFFF"
            )
        )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        trxs = []
        for i in range(4):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=estimate_result["nonce"],
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )

        tree_acc_data.add_trx(trxs[0], 3, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 3, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user,
            treasury_pool,
            tree_acc_data.data,
        )

        # evm_loader.assemble_container(
        #     operator.operator_keypairs[0],
        #     treasury_pool,
        #     evm_loader.ether2program(alt_contract_containerized.address[2:]),
        #     [evm_loader.ether2balance(neon_user.neon_address, web3_client_sol.chain_id)],
        # )
        #

        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            check_trx_is_success(web3_client_sol, evm_loader, trx.hash().hex(), timeout=120)

        wait_condition(lambda: not evm_loader.account_exists(tree_account), timeout_sec=120, delay=2)

    def test_erc20_for_spl_containerized(self, accounts, evm_loader, multiple_actions_erc20, treasury_pool, operator):

        acc_1, contract = multiple_actions_erc20
        acc_2 = accounts[2]
        mint_amount = 1000
        transfer_amount_1 = 300
        transfer_amount_2 = 200

        container_address = evm_loader.ether2program(contract.address[2:])
        erc20_address = contract.functions.getErc20Address().call()
        erc20_sol_address = evm_loader.ether2program(erc20_address[2:])

        tx = self.web3_client.make_raw_tx(acc_1)
        instruction_tx = contract.functions.mintTransferTransfer(
            mint_amount,
            acc_1.address,
            transfer_amount_1,
            acc_2.address,
            transfer_amount_2,
        ).build_transaction(tx)

        sol_accounts = get_accounts_for_container_by_emulation(
            self.web3_client, evm_loader, instruction_tx, acc_1, container_address
        )
        balance_accounts = evm_loader.filter_neon_accounts_by_type(sol_accounts, AccountType.USER_BALANCE)

        evm_loader.assemble_container(operator.operator_keypairs[0], treasury_pool, container_address, balance_accounts)
        evm_loader.allocate_container(operator.operator_keypairs[0], treasury_pool, container_address, 5000)
        evm_loader.allocate_container(operator.operator_keypairs[0], treasury_pool, container_address, 5000)

        evm_loader.assemble_container(
            operator.operator_keypairs[0],
            treasury_pool,
            container_address,
            [erc20_sol_address],
        )

        receipt = self.web3_client.send_transaction(acc_1, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

    def test_resize_and_change_data_in_container(
        self, evm_loader, operator, treasury_pool, accounts, storage_resize_checker_containerized
    ):
        caller_sol_address = evm_loader.ether2program(storage_resize_checker_containerized.address[2:])
        container_size_before = len(evm_loader.get_solana_account_data(caller_sol_address))

        for _ in range(3):
            tx = self.web3_client.make_raw_tx(accounts[0], amount=1000)
            instruction_tx = storage_resize_checker_containerized.functions.callAndChange(
                gen_hash_of_block(1000)
            ).build_transaction(tx)
            resp = self.web3_client.send_transaction(accounts[0], instruction_tx)
            assert resp["status"] == 1

            container_size = len(evm_loader.get_solana_account_data(caller_sol_address))
            assert container_size > container_size_before, "Container size should be increased"
            container_size_before = container_size

    def test_container_with_solana_composability_calls(
        self, evm_loader, call_solana_caller, solana_account, operator, treasury_pool
    ):
        loops = 20
        sender = self.accounts[0]
        from_wallet = solana_account
        to_wallet = Keypair()
        amount = 100000

        serialized, mint, accounts_list = prepare_transfer_spl_data(
            evm_loader, from_wallet, to_wallet, amount, call_solana_caller
        )
        tx = self.web3_client.make_raw_tx(from_=sender)
        instruction_tx = call_solana_caller.functions.executeInIterativeMode(loops, 0, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1
        sol_accounts_for_trx_without_container = get_sol_account_list_by_neon_trx(
            self.web3_client, evm_loader, resp["transactionHash"].hex()
        )

        assert int(mint.get_balance(accounts_list[1], commitment=Confirmed).value.amount) == amount
        container_address = evm_loader.ether2program(call_solana_caller.address[2:])
        account_for_container = get_accounts_for_container_by_emulation(
            self.web3_client, evm_loader, instruction_tx, sender, container_address
        )

        evm_loader.assemble_container(
            operator=operator.operator_keypairs[0],
            treasury=treasury_pool,
            container_address=evm_loader.ether2program(call_solana_caller.address[2:]),
            accounts=account_for_container,
        )

        tx = self.web3_client.make_raw_tx(from_=sender)
        instruction_tx = call_solana_caller.functions.executeInIterativeMode(loops, 0, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1
        sol_accounts_for_trx_with_container = get_sol_account_list_by_neon_trx(
            self.web3_client, evm_loader, resp["transactionHash"].hex()
        )
        assert len(sol_accounts_for_trx_with_container) < len(
            sol_accounts_for_trx_without_container
        ), "Transaction with container should use less accounts than without it"
