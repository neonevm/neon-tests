import random
from copy import copy

import allure
import eth_abi
from eth_utils import abi
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from utils import instructions
from utils.consts import QUERY_ACCOUNT_ID, REMAPPING_ZEPPELIN
from utils.evm_loader import EvmLoader
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction
from utils.types import TreasuryPool, Caller, Contract
from .utils import ethereum as eth_utils
from .utils.contract import get_contract_bin
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text
from .utils.neon_api_rpc_client import NeonApiRpcClient

EXPECTED_CU_DELTA = 60


class TestSimulateSolana:
    @staticmethod
    @allure.step("Simulate and execute Solana transaction")
    def _simulate_and_execute_tx(
        sol_tx: Transaction,
        neon_rpc_client: NeonApiRpcClient,
        evm_loader: EvmLoader,
        operator_keypair: Keypair,
        done_simulation: bool,
        done_execution: bool,
        simulated_compute_units: int,
        actual_compute_units: int,
    ) -> tuple[bool, bool]:
        sol_trx_with_compute_budget = copy(sol_tx)
        sol_trx_with_compute_budget = sol_trx_with_compute_budget.add(
            instructions.TransactionWithComputeBudget(operator_keypair)
        )
        # Simulate the transaction
        if not done_simulation:
            assert not done_execution, "Execution completed but simulation is still going"
            simulate_response = neon_rpc_client.simulate_solana(sol_tx.instructions)

            simulated_instructions = simulate_response["instructions"]

            simulated_compute_units += sum(
                [simulate_result["executed_units"] for simulate_result in simulated_instructions]
            )

            for simulated_transaction in simulated_instructions:
                if simulated_transaction["error"]:
                    raise AssertionError(f"Error in sol trx: {simulated_transaction}")

                for log in simulated_transaction["logs"]:
                    if "ExitError" in log:
                        raise AssertionError(f"EVM Return error in logs: {simulated_transaction}")

                    elif "exit_status" in log:
                        done_simulation = True
                        break

        # Execute the transaction
        if not done_execution:
            executed_sol_tx = evm_loader.send_tx_and_check_status_ok(sol_trx_with_compute_budget, operator_keypair)
            actual_compute_units += executed_sol_tx.value.transaction.meta.compute_units_consumed

            for log in executed_sol_tx.value.transaction.meta.log_messages:
                if "exit_status" in log:
                    done_execution = True
                    assert done_simulation, "Execution completed but simulation is still going"
                    break

        return done_simulation, done_execution

    @staticmethod
    def _check_simulation_is_successful(simulate_response):
        simulated_instructions = simulate_response["instructions"]
        for simulated_transaction in simulated_instructions:
            if simulated_transaction["error"]:
                raise AssertionError(f"Error in sol trx: {simulated_transaction}")
            assert "Program log: exit_status=0x11" in simulated_transaction["logs"]

    @allure.step("Get sum of compute units from simulation")
    def _get_compute_units_from_simulation(
        self, neon_rpc_client: NeonApiRpcClient, sol_tx: Transaction, solana_overrides_params=None
    ) -> int:
        simulate_response = neon_rpc_client.simulate_solana(sol_tx.instructions, solana_overrides_params)
        simulated_compute_units = sum(
            [simulate_result["executed_units"] for simulate_result in simulate_response["instructions"]]
        )
        return simulated_compute_units

    def test_simulate_solana_send_neon_from_holder_account(
        self,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        session_user: Caller,
    ):
        # Create Neon transaction and write it to a holder account
        amount = 1
        neon_signed_tx = eth_utils.make_eth_transaction(
            evm_loader=evm_loader,
            to_addr=session_user.eth_address,
            data=None,
            caller=sender_with_tokens,
            value=amount,
        )
        evm_loader.write_transaction_to_holder_account(neon_signed_tx, holder_acc, operator_keypair)

        # Create Solana transaction
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_execute_from_account(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                evm_loader_id=evm_loader.loader_id,
                holder_address=holder_acc,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
            )
        )
        simulated_compute_units = self._get_compute_units_from_simulation(neon_rpc_client, sol_tx)

        # Execute the transaction
        executed_sol_tx = evm_loader.send_tx_and_check_status_ok(sol_tx, operator_keypair)
        actual_compute_units = executed_sol_tx.value.transaction.meta.compute_units_consumed

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < EXPECTED_CU_DELTA, msg

    def test_simulate_solana_send_neon_from_instruction(
        self,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        session_user,
    ):
        # Create Neon transaction
        amount = 1
        neon_signed_tx = eth_utils.make_eth_transaction(
            evm_loader=evm_loader,
            to_addr=session_user.eth_address,
            data=None,
            caller=sender_with_tokens,
            value=amount,
        )

        # Create Solana transaction
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_execute_from_instruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=neon_signed_tx.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
            )
        )

        # Simulate the transaction
        simulated_compute_units = self._get_compute_units_from_simulation(neon_rpc_client, sol_tx)
        # Execute the transaction
        executed_sol_tx = evm_loader.send_tx_and_check_status_ok(sol_tx, operator_keypair)
        actual_compute_units = executed_sol_tx.value.transaction.meta.compute_units_consumed

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < EXPECTED_CU_DELTA, msg

    def test_simulate_solana_iterative_from_holder_account(
        self,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        multiple_actions_erc20: Contract,
        session_user: Caller,
    ):
        # Create Neon transaction and write it to a holder account
        function_signature = "mintMintTransferTransferMintMintTransferTransfer(uint256,uint256,address)"
        params = [10000, 10000, session_user.eth_address]

        additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=multiple_actions_erc20.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )

        neon_signed_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=multiple_actions_erc20,
            function_signature=function_signature,
            params=params,
        )

        evm_loader.write_transaction_to_holder_account(neon_signed_tx, holder_acc, operator_keypair)

        simulated_compute_units = actual_compute_units = 0

        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_step_from_account(
                step_count=500,
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                evm_loader_id=evm_loader.loader_id,
                holder_address=holder_acc,
                treasury=treasury_pool,
                additional_accounts=additional_accounts,
            )
        )
        done = done_simulation = done_execution = False

        while not done:
            done_simulation, done_execution = self._simulate_and_execute_tx(
                sol_tx=sol_tx,
                neon_rpc_client=neon_rpc_client,
                evm_loader=evm_loader,
                operator_keypair=operator_keypair,
                done_simulation=done_simulation,
                done_execution=done_execution,
                simulated_compute_units=simulated_compute_units,
                actual_compute_units=actual_compute_units,
            )

            done = done_simulation and done_execution

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < EXPECTED_CU_DELTA, msg

    def test_simulate_solana_iterative_deployment_from_holder_account(
        self,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        # Create Neon transaction and write it to a holder account
        contract_file_name = "external/neon-contracts/contracts/token/ERC20ForSpl/erc20_for_spl_factory.sol"
        contract_name = "ERC20ForSplFactory"
        version = "0.8.28"
        encoded_args = b""

        contract_code = get_contract_bin(
            contract=contract_file_name,
            contract_name=contract_name,
            version=version,
            import_remappings=REMAPPING_ZEPPELIN,
        )

        emulate_result = neon_rpc_client.emulate(
            sender_with_tokens.eth_address.hex(),
            contract=None,
            data=contract_code + encoded_args.hex(),
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        signed_tx = eth_utils.make_deployment_transaction(
            evm_loader,
            sender_with_tokens,
            contract_file_name,
            contract_name,
            encoded_args=encoded_args,
            version=version,
            import_remappings=REMAPPING_ZEPPELIN,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        simulated_compute_units = actual_compute_units = 0
        done = done_simulation = done_execution = False
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_step_from_account(
                step_count=500,
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                evm_loader_id=evm_loader.loader_id,
                holder_address=holder_acc,
                treasury=treasury_pool,
                additional_accounts=additional_accounts,
            )
        )
        while not done:
            # Create a Solana transaction
            done_simulation, done_execution = self._simulate_and_execute_tx(
                sol_tx=sol_tx,
                neon_rpc_client=neon_rpc_client,
                evm_loader=evm_loader,
                operator_keypair=operator_keypair,
                done_simulation=done_simulation,
                done_execution=done_execution,
                simulated_compute_units=simulated_compute_units,
                actual_compute_units=actual_compute_units,
            )

            done = done_simulation and done_execution

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < EXPECTED_CU_DELTA, msg

    def test_simulate_solana_iterative_from_instruction(
        self,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        rw_lock_contract: Contract,
    ):
        # Create Neon transaction
        function_signature = "update_storage(uint256)"
        params = [10]
        neon_signed_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=rw_lock_contract,
            function_signature=function_signature,
            params=params,
        )

        # Emulate transaction
        additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=rw_lock_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )

        simulated_compute_units = actual_compute_units = index = 0
        done = done_simulation = done_execution = False

        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_step_from_instruction(
                index=index,
                step_count=500,
                instruction=neon_signed_tx.raw_transaction,
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                evm_loader_id=evm_loader.loader_id,
                storage_address=holder_acc,
                treasury=treasury_pool,
                additional_accounts=additional_accounts,
            )
        )
        while not done:
            done_simulation, done_execution = self._simulate_and_execute_tx(
                sol_tx=sol_tx,
                neon_rpc_client=neon_rpc_client,
                evm_loader=evm_loader,
                operator_keypair=operator_keypair,
                done_simulation=done_simulation,
                done_execution=done_execution,
                simulated_compute_units=simulated_compute_units,
                actual_compute_units=actual_compute_units,
            )

            index += 1
            done = done_simulation and done_execution

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < EXPECTED_CU_DELTA, msg

    def test_simulate_solana_call_precompiled_contract(
        self,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        session_user: Caller,
        query_account_caller_contract: Contract,
    ):
        # Create Neon transaction
        solana_account_address_uint256 = int.from_bytes(session_user.solana_account_address, byteorder="big")
        neon_signed_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=query_account_caller_contract,
            function_signature="queryOwner(uint256)",
            params=[solana_account_address_uint256],
        )

        # Create Solana transaction
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_execute_from_instruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=neon_signed_tx.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    query_account_caller_contract.solana_address,
                    session_user.solana_account_address,
                    QUERY_ACCOUNT_ID,
                ],
            )
        )

        simulated_compute_units = self._get_compute_units_from_simulation(neon_rpc_client, sol_tx)

        # Execute the transaction
        executed_sol_tx = evm_loader.send_tx_and_check_status_ok(sol_tx, operator_keypair)
        actual_compute_units = executed_sol_tx.value.transaction.meta.compute_units_consumed

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < EXPECTED_CU_DELTA, msg

    def test_simulate_solana_scheduled_transaction(
        self,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        basic_contract: Contract,
        neon_user_func_scope: NeonUser,
    ):
        nonce = evm_loader.get_neon_nonce(neon_user_func_scope.neon_address)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx = ScheduledTransaction(
            neon_user_func_scope.neon_address,
            None,
            nonce,
            0,
            target=basic_contract.eth_address,
            value=0,
            call_data=data,
            chain_id=evm_loader.sol_chain_id,
        )
        tree_account = evm_loader.create_tree_account(neon_user_func_scope, treasury_pool, tx.encode())
        evm_loader.write_transaction_to_holder_account(tx.encode(), holder_acc, operator_keypair)
        neon_user_balance_account = neon_user_func_scope.get_balance_account(evm_loader.sol_chain_id)
        additional_accounts = [basic_contract.solana_address, neon_user_balance_account]

        simulated_compute_units = actual_compute_units = 0

        # Start scheduled transaction (simulation and execution)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair, evm_loader.sol_chain_id)

        start_scheduled_transaction_tx = Transaction()
        start_scheduled_transaction_tx.add(
            instructions.make_scheduled_transaction_start_from_account(
                0,
                operator_keypair,
                operator_balance_pubkey,
                evm_loader.loader_id,
                holder_acc,
                tree_account,
                additional_accounts,
            )
        )

        simulated_compute_units += self._get_compute_units_from_simulation(
            neon_rpc_client, start_scheduled_transaction_tx
        )

        start_scheduled_transaction_tx_receipt = evm_loader.send_tx_and_check_status_ok(
            start_scheduled_transaction_tx,
            operator_keypair,
        )
        actual_compute_units += start_scheduled_transaction_tx_receipt.value.transaction.meta.compute_units_consumed

        # Execute scheduled transaction steps (simulation and execution)

        sol_tx = Transaction()
        sol_tx.add(
            instructions.make_transaction_step_from_account(
                step_count=500,
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                evm_loader_id=evm_loader.loader_id,
                holder_address=holder_acc,
                treasury=treasury_pool,
                additional_accounts=additional_accounts,
            )
        )
        done = done_simulation = done_execution = False
        while not done:
            done_simulation, done_execution = self._simulate_and_execute_tx(
                sol_tx=sol_tx,
                neon_rpc_client=neon_rpc_client,
                evm_loader=evm_loader,
                operator_keypair=operator_keypair,
                done_simulation=done_simulation,
                done_execution=done_execution,
                simulated_compute_units=simulated_compute_units,
                actual_compute_units=actual_compute_units,
            )
            done = done_simulation and done_execution

        # Finish scheduled transaction steps (simulation and execution)
        finish_trx = Transaction()
        finish_trx.add(
            instructions.make_scheduled_transaction_finish(
                operator_keypair.pubkey(),
                operator_balance_pubkey,
                evm_loader.loader_id,
                holder_acc,
                tree_account,
            )
        )

        simulated_compute_units += self._get_compute_units_from_simulation(neon_rpc_client, finish_trx)
        finish_receipt = evm_loader.send_tx_and_check_status_ok(finish_trx, operator_keypair)
        actual_compute_units += finish_receipt.value.transaction.meta.compute_units_consumed

        # Destroy tree account transaction steps (simulation and execution)
        destroy_trx = Transaction()
        destroy_trx.add(
            instructions.make_scheduled_transaction_destroy(
                signer=operator_keypair.pubkey(),
                balance_account=neon_user_balance_account,
                treasury=treasury_pool,
                tree_account=tree_account,
                evm_loader_id=evm_loader.loader_id,
            )
        )

        simulated_compute_units += self._get_compute_units_from_simulation(neon_rpc_client, destroy_trx)

        destroy_receipt = evm_loader.send_tx_and_check_status_ok(destroy_trx, operator_keypair)
        actual_compute_units += destroy_receipt.value.transaction.meta.compute_units_consumed

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < EXPECTED_CU_DELTA * 3, msg

    def test_simulate_solana_with_solana_overrides_data_account(
        self,
        storage_checker_contract: Contract,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        def execute_trx(function_signature, params, add_accounts):
            signed_tx = eth_utils.make_contract_call_trx(
                evm_loader=evm_loader,
                user=sender_with_tokens,
                contract=storage_checker_contract,
                function_signature=function_signature,
                params=params,
            )

            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, add_accounts
            )
            check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        update_b_function_signature = "update_b(uint256)"
        # value = 239 is hardcoded in solidity contract to be checked with check_b() method
        update_b_params = [239]

        additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=storage_checker_contract.eth_address.hex(),
            function_signature=update_b_function_signature,
            params=update_b_params,
        )
        execute_trx(update_b_function_signature, update_b_params, additional_accounts)

        accounts = [
            sender_with_tokens.balance_account_address,
            storage_checker_contract.solana_address,
        ]
        data_account = list(set(additional_accounts) - set(accounts))[0]
        account_info_after_tx1 = evm_loader.get_account_info(data_account, commitment=Confirmed)

        execute_trx(update_b_function_signature, [192], additional_accounts)
        account_info_after_tx2 = evm_loader.get_account_info(data_account, commitment=Confirmed)

        assert account_info_after_tx1.value.data != account_info_after_tx2.value.data

        # Create Solana transaction
        tx_for_simulation = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=storage_checker_contract,
            function_signature="check_b()",
        )
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_execute_from_instruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=tx_for_simulation.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    storage_checker_contract.solana_address,
                    data_account,
                ],
            )
        )

        # Simulate the transaction
        account_info_override = {
            "lamports": account_info_after_tx1.value.lamports,
            "data": account_info_after_tx1.value.data.hex(),
            "owner": str(account_info_after_tx1.value.owner),
            "executable": account_info_after_tx1.value.executable,
            "rent_epoch": account_info_after_tx1.value.rent_epoch,
        }

        simulate_response = neon_rpc_client.simulate_solana(
            instructions=sol_tx.instructions,
            accounts_overrides={str(data_account): account_info_override},
        )

        self._check_simulation_is_successful(simulate_response)

    def test_simulate_solana_with_solana_overrides_multiple_data_accounts(
        self,
        storage_checker_contract: Contract,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        def execute_trx(func_signature, parameters, add_accounts):
            signed_tx = eth_utils.make_contract_call_trx(
                evm_loader=evm_loader,
                user=sender_with_tokens,
                contract=storage_checker_contract,
                function_signature=func_signature,
                params=parameters,
            )

            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, add_accounts
            )
            check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        function_signature = "update_data(uint256,uint256)"
        # value = 123 is hardcoded in solidity contract to be checked with check_data(uint256) method
        params = [3, 123]

        additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=storage_checker_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        execute_trx(function_signature, params, additional_accounts)

        accounts = [
            sender_with_tokens.balance_account_address,
            storage_checker_contract.solana_address,
        ]
        data_accounts = list(set(additional_accounts) - set(accounts))

        accounts_info_after_tx1 = []
        for account in data_accounts:
            accounts_info_after_tx1.append(evm_loader.get_account_info(account, commitment=Confirmed))

        execute_trx(function_signature, [3, 398], additional_accounts)

        accounts_info_after_tx2 = []
        for account in data_accounts:
            accounts_info_after_tx2.append(evm_loader.get_account_info(account, commitment=Confirmed))

        for i in range(len(accounts_info_after_tx1)):
            assert accounts_info_after_tx2[i].value.data != accounts_info_after_tx1[i].value.data

        # Create Solana transaction
        tx_for_simulation = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=storage_checker_contract,
            function_signature="check_data(uint256)",
            params=[3],
        )
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_execute_from_instruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=tx_for_simulation.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    storage_checker_contract.solana_address,
                    data_accounts[0],
                    data_accounts[1],
                    data_accounts[2],
                ],
            )
        )

        accounts_info_override = []
        for account_info in accounts_info_after_tx1:
            accounts_info_override.append(
                {
                    "lamports": account_info.value.lamports,
                    "data": account_info.value.data.hex(),
                    "owner": str(account_info.value.owner),
                    "executable": account_info.value.executable,
                    "rent_epoch": account_info.value.rent_epoch,
                }
            )

        solana_overrides_params = {}
        for i in range(len(data_accounts)):
            solana_overrides_params[str(data_accounts[i])] = accounts_info_override[i]

        simulate_response = neon_rpc_client.simulate_solana(
            instructions=sol_tx.instructions,
            accounts_overrides=solana_overrides_params,
        )

        self._check_simulation_is_successful(simulate_response)

    def test_simulate_solana_with_solana_overrides_balance_account(
        self,
        storage_checker_contract: Contract,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        session_user: Caller,
    ):
        def execute_trx(func_signature, parameters, add_accounts):
            signed_tx = eth_utils.make_contract_call_trx(
                evm_loader=evm_loader,
                user=sender_with_tokens,
                contract=storage_checker_contract,
                function_signature=func_signature,
                params=parameters,
            )

            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, add_accounts
            )
            check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        recipient = session_user
        recipient_balance_before = evm_loader.get_neon_balance(recipient.eth_address)
        balance_account = storage_checker_contract.balance_account_address
        evm_loader.deposit_neon(operator_keypair, storage_checker_contract.eth_address, 1000000)
        amount = evm_loader.get_neon_balance(storage_checker_contract.eth_address)

        function_signature = "send_neon(address,uint256)"
        params = [recipient.eth_address.hex(), amount // 2]

        account_info_full_balance = evm_loader.get_account_info(balance_account, commitment=Confirmed)

        additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=storage_checker_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        execute_trx(function_signature, params, additional_accounts)

        recipient_balance_after = evm_loader.get_neon_balance(recipient.eth_address)
        assert recipient_balance_after == recipient_balance_before + amount // 2

        account_info_after_tx = evm_loader.get_account_info(balance_account, commitment=Confirmed)
        assert account_info_full_balance.value.data != account_info_after_tx.value.data

        contract_balance = evm_loader.get_neon_balance(storage_checker_contract.eth_address)
        assert contract_balance < amount

        # Create Solana transaction
        tx_for_simulation = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=storage_checker_contract,
            function_signature=function_signature,
            params=[recipient.eth_address.hex(), amount],
        )
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_execute_from_instruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=tx_for_simulation.raw_transaction,
                additional_accounts=additional_accounts,
            )
        )

        account_info_override = {
            "lamports": account_info_full_balance.value.lamports,
            "data": account_info_full_balance.value.data.hex(),
            "owner": str(account_info_full_balance.value.owner),
            "executable": account_info_full_balance.value.executable,
            "rent_epoch": account_info_full_balance.value.rent_epoch,
        }

        simulate_response = neon_rpc_client.simulate_solana(
            instructions=sol_tx.instructions,
            accounts_overrides={str(balance_account): account_info_override},
        )
        self._check_simulation_is_successful(simulate_response)

    def test_simulate_solana_with_solana_overrides_absent_field(
        self,
        storage_checker_contract: Contract,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        function_signature = "update_b(uint256)"
        params = [4021]

        additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=storage_checker_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )

        signed_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=storage_checker_contract,
            function_signature=function_signature,
            params=params,
        )

        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder_acc, additional_accounts
        )
        check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        accounts = [
            sender_with_tokens.balance_account_address,
            storage_checker_contract.solana_address,
        ]
        data_account = list(set(additional_accounts) - set(accounts))[0]
        account_info = evm_loader.get_account_info(data_account, commitment=Confirmed)

        # Create Solana transaction
        tx_for_simulation = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=storage_checker_contract,
            function_signature=function_signature,
            params=params,
        )
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_execute_from_instruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=tx_for_simulation.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    storage_checker_contract.solana_address,
                    data_account,
                ],
            )
        )

        account_info_override = {
            "lamports": account_info.value.lamports,
            "data": account_info.value.data.hex(),
            "owner": str(account_info.value.owner),
            "executable": account_info.value.executable,
            "rent_epoch": account_info.value.rent_epoch,
        }
        keys = ["lamports", "data", "owner", "executable", "rent_epoch"]
        del account_info_override[random.SystemRandom().choice(keys)]

        simulate_response = neon_rpc_client.simulate_solana(
            instructions=sol_tx.instructions,
            accounts_overrides={str(data_account): account_info_override},
        )
        assert "Invalid params" == simulate_response["message"]
        assert 'Error("missing field ' in simulate_response["data"]

    def test_simulate_solana_compare_cu_with_solana_overrides_and_without(
        self,
        storage_checker_contract: Contract,
        sender_with_tokens: Caller,
        neon_rpc_client: NeonApiRpcClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        def execute_trx(func_signature, parameters, add_accounts):
            signed_tx = eth_utils.make_contract_call_trx(
                evm_loader=evm_loader,
                user=sender_with_tokens,
                contract=storage_checker_contract,
                function_signature=func_signature,
                params=parameters,
            )

            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, add_accounts
            )
            check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        function_signature = "update_b(uint256)"
        params = [284]

        additional_accounts = neon_rpc_client.get_additional_accounts_by_emulation(
            sender=sender_with_tokens.eth_address.hex(),
            contract=storage_checker_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        execute_trx(function_signature, params, additional_accounts)

        accounts = [
            sender_with_tokens.balance_account_address,
            storage_checker_contract.solana_address,
        ]
        data_account = list(set(additional_accounts) - set(accounts))[0]
        account_info_after_tx1 = evm_loader.get_account_info(data_account, commitment=Confirmed)

        execute_trx(function_signature, [125], additional_accounts)

        # Create Solana transaction
        tx_for_simulation = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=storage_checker_contract,
            function_signature=function_signature,
            params=params,
        )
        sol_tx = Transaction()
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_transaction_execute_from_instruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=tx_for_simulation.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    storage_checker_contract.solana_address,
                    data_account,
                ],
            )
        )

        account_info_override = {
            "lamports": account_info_after_tx1.value.lamports,
            "data": account_info_after_tx1.value.data.hex(),
            "owner": str(account_info_after_tx1.value.owner),
            "executable": account_info_after_tx1.value.executable,
            "rent_epoch": account_info_after_tx1.value.rent_epoch,
        }

        simulate_response_with_override = neon_rpc_client.simulate_solana(
            instructions=sol_tx.instructions,
            accounts_overrides={str(data_account): account_info_override},
        )

        simulate_response = neon_rpc_client.simulate_solana(sol_tx.instructions)
        self._check_simulation_is_successful(simulate_response)
        self._check_simulation_is_successful(simulate_response_with_override)
        executed_units_without_override = self._get_compute_units_from_simulation(neon_rpc_client, sol_tx)
        executed_units_with_override = self._get_compute_units_from_simulation(
            neon_rpc_client, sol_tx, {str(data_account): account_info_override}
        )

        assert executed_units_with_override < executed_units_without_override, (
            f"Executed compute units with override {executed_units_with_override} "
            f"should be less than without override {executed_units_without_override}"
        )

    def test_unsupported_program_id(self, neon_rpc_client, operator_keypair):
        trx = instructions.TransactionWithComputeBudget(operator_keypair)
        resp = neon_rpc_client.simulate_solana(trx.instructions)
        assert "Solana Simulator error UnsupportedAccount" in resp["message"]
