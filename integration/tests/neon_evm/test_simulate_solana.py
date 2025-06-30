import random
import allure
import base58
import eth_abi
from eth_utils import abi
from solana.rpc.commitment import Finalized, Confirmed
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
from .utils.neon_api_client import NeonApiClient
from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text


class TestSimulateSolana:
    @staticmethod
    @allure.step("Simulate and execute Solana transaction")
    def _simulate_and_execute_tx(
        sol_tx: Transaction,
        neon_api_client: NeonApiClient,
        evm_loader: EvmLoader,
        operator_keypair: Keypair,
        done_simulation: bool,
        done_execution: bool,
        simulated_compute_units: int,
        actual_compute_units: int,
    ) -> tuple[bool, bool]:
        # Simulate the transaction
        if not done_simulation:
            assert not done_execution, "Execution completed but simulation is still going"

            serialized_transaction = sol_tx.serialize()
            hex_serialized_transaction = serialized_transaction.hex()
            blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()
            simulate_response = neon_api_client.simulate_solana(
                blockhash=blockhash,
                transactions=[hex_serialized_transaction],
            )
            simulated_transactions = simulate_response.json()["value"]["transactions"]

            simulated_compute_units += sum(
                [simulate_result["executed_units"] for simulate_result in simulated_transactions]
            )

            for simulated_transaction in simulated_transactions:
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
            executed_sol_tx = evm_loader.send_tx(sol_tx, operator_keypair)
            actual_compute_units += executed_sol_tx.value.transaction.meta.compute_units_consumed

            if executed_sol_tx.value.transaction.meta.err:
                raise AssertionError(f"Error in sol trx: {executed_sol_tx}")

            for log in executed_sol_tx.value.transaction.meta.log_messages:
                if "ExitError" in log:
                    raise AssertionError(f"EVM Return error in logs: {executed_sol_tx}")

                elif "exit_status" in log:
                    done_execution = True
                    assert done_simulation, "Execution completed but simulation is still going"
                    break

        return done_simulation, done_execution

    def test_simulate_solana_send_neon_from_holder_account(
        self,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
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
        sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_ExecuteTrxFromAccount(
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
        sol_tx.sign(operator_keypair)

        # Simulate the transaction
        serialized_transaction = sol_tx.serialize()
        hex_serialized_transaction = serialized_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()
        simulate_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_transaction],
        )
        simulated_compute_units = sum(
            [simulate_result["executed_units"] for simulate_result in simulate_response.json()["value"]["transactions"]]
        )

        # Execute the transaction
        executed_sol_tx = evm_loader.send_tx(sol_tx, operator_keypair)
        actual_compute_units = executed_sol_tx.value.transaction.meta.compute_units_consumed

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < 10, msg

    def test_simulate_solana_send_neon_from_instruction(
        self,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
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
        sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_ExecuteTrxFromInstruction(
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
        sol_tx.sign(operator_keypair)

        # Simulate the transaction
        serialized_transaction = sol_tx.serialize()
        hex_serialized_transaction = serialized_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()
        simulate_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_transaction],
        )
        simulated_compute_units = sum(
            [simulate_result["executed_units"] for simulate_result in simulate_response.json()["value"]["transactions"]]
        )

        # Execute the transaction
        executed_sol_tx = evm_loader.send_tx(sol_tx, operator_keypair)
        actual_compute_units = executed_sol_tx.value.transaction.meta.compute_units_consumed

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < 10, msg

    def test_simulate_solana_iterative_from_holder_account(
        self,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
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

        emulate_result = neon_api_client.emulate_contract_call(
            sender=sender_with_tokens.eth_address.hex(),
            contract=multiple_actions_erc20.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        neon_signed_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=multiple_actions_erc20,
            function_signature=function_signature,
            params=params,
        )

        evm_loader.write_transaction_to_holder_account(neon_signed_tx, holder_acc, operator_keypair)

        simulated_compute_units = actual_compute_units = 0
        done = done_simulation = done_execution = False

        while not done:
            # Create a Solana transaction
            sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
            operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
            sol_tx.add(
                instructions.make_ExecuteTrxFromAccountDataIterativeOrContinue(
                    step_count=500,
                    operator=operator_keypair,
                    operator_balance=operator_balance_pubkey,
                    evm_loader_id=evm_loader.loader_id,
                    holder_address=holder_acc,
                    treasury=treasury_pool,
                    additional_accounts=additional_accounts,
                )
            )
            sol_tx.sign(operator_keypair)

            done_simulation, done_execution = self._simulate_and_execute_tx(
                sol_tx=sol_tx,
                neon_api_client=neon_api_client,
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
        assert abs(simulated_compute_units - actual_compute_units) < 10, msg

    def test_simulate_solana_iterative_deployment_from_holder_account(
        self,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        # Create Neon transaction and write it to a holder account
        chain_id = evm_loader.chain_id
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

        emulate_result = neon_api_client.emulate(
            sender_with_tokens.eth_address.hex(),
            contract=None,
            data=contract_code + encoded_args.hex(),
            chain_id=chain_id,
            value=hex(0),
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        signed_tx = eth_utils.make_deployment_transaction(
            evm_loader,
            sender_with_tokens,
            contract_file_name,
            contract_name,
            encoded_args=encoded_args,
            value=0,
            version=version,
            chain_id=chain_id,
            import_remappings=REMAPPING_ZEPPELIN,
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        simulated_compute_units = actual_compute_units = 0
        done = done_simulation = done_execution = False

        while not done:
            # Create a Solana transaction
            sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
            operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
            sol_tx.add(
                instructions.make_ExecuteTrxFromAccountDataIterativeOrContinue(
                    step_count=500,
                    operator=operator_keypair,
                    operator_balance=operator_balance_pubkey,
                    evm_loader_id=evm_loader.loader_id,
                    holder_address=holder_acc,
                    treasury=treasury_pool,
                    additional_accounts=additional_accounts,
                )
            )
            sol_tx.sign(operator_keypair)

            done_simulation, done_execution = self._simulate_and_execute_tx(
                sol_tx=sol_tx,
                neon_api_client=neon_api_client,
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
        assert abs(simulated_compute_units - actual_compute_units) < 10, msg

    def test_simulate_solana_iterative_from_instruction(
        self,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
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
        emulate_result = neon_api_client.emulate_contract_call(
            sender=sender_with_tokens.eth_address.hex(),
            contract=rw_lock_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        simulated_compute_units = actual_compute_units = index = 0
        done = done_simulation = done_execution = False

        while not done:
            # Create a Solana transaction
            sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
            operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
            sol_tx.add(
                instructions.make_PartialCallOrContinueFromRawEthereumTX(
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
            sol_tx.sign(operator_keypair)
            done_simulation, done_execution = self._simulate_and_execute_tx(
                sol_tx=sol_tx,
                neon_api_client=neon_api_client,
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
        assert abs(simulated_compute_units - actual_compute_units) < 10, msg

    def test_simulate_solana_call_precompiled_contract(
        self,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
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
        sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_ExecuteTrxFromInstruction(
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
        sol_tx.sign(operator_keypair)

        # Simulate the transaction
        serialized_transaction = sol_tx.serialize()
        hex_serialized_transaction = serialized_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()
        simulate_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_transaction],
        )
        simulated_compute_units = sum(
            [simulate_result["executed_units"] for simulate_result in simulate_response.json()["value"]["transactions"]]
        )

        # Execute the transaction
        executed_sol_tx = evm_loader.send_tx(sol_tx, operator_keypair)
        actual_compute_units = executed_sol_tx.value.transaction.meta.compute_units_consumed

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < 10, msg

    def test_simulate_solana_scheduled_transaction(
        self,
        neon_api_client: NeonApiClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        session_user: Caller,
        basic_contract: Contract,
        neon_user: NeonUser,
    ):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address)
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
        evm_loader.write_transaction_to_holder_account(tx.encode(), holder_acc, operator_keypair)
        neon_user_balance_account = neon_user.get_balance_account(evm_loader.sol_chain_id)
        additional_accounts = [basic_contract.solana_address, neon_user_balance_account]

        simulated_compute_units = actual_compute_units = 0

        # Start scheduled transaction (simulation and execution)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair, evm_loader.sol_chain_id)

        start_scheduled_transaction_tx = instructions.TransactionWithComputeBudget(
            operator_keypair,
            compute_unit_price=1000000,
        )
        start_scheduled_transaction_tx.add(
            instructions.make_ScheduledTransactionStartFromAccount(
                0,
                operator_keypair,
                operator_balance_pubkey,
                evm_loader.loader_id,
                holder_acc,
                tree_account,
                additional_accounts,
            )
        )
        start_scheduled_transaction_tx.sign(operator_keypair)

        serialized_start_transaction = start_scheduled_transaction_tx.serialize()
        hex_serialized_start_transaction = serialized_start_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()
        simulate_start_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_start_transaction],
        )
        simulated_start_transactions = simulate_start_response.json()["value"]["transactions"]
        simulated_compute_units += sum(
            [simulate_result["executed_units"] for simulate_result in simulated_start_transactions]
        )

        start_scheduled_transaction_tx_receipt = evm_loader.send_tx(
            start_scheduled_transaction_tx,
            operator_keypair,
        )
        actual_compute_units += start_scheduled_transaction_tx_receipt.value.transaction.meta.compute_units_consumed

        # Execute scheduled transaction steps (simulation and execution)
        done = done_simulation = done_execution = False

        while not done:
            # Create a Solana transaction
            sol_tx = instructions.TransactionWithComputeBudget(operator_keypair, compute_unit_price=3929)
            sol_tx.add(
                instructions.make_ExecuteTrxFromAccountDataIterativeOrContinue(
                    step_count=500,
                    operator=operator_keypair,
                    operator_balance=operator_balance_pubkey,
                    evm_loader_id=evm_loader.loader_id,
                    holder_address=holder_acc,
                    treasury=treasury_pool,
                    additional_accounts=additional_accounts,
                )
            )
            sol_tx.sign(operator_keypair)

            done_simulation, done_execution = self._simulate_and_execute_tx(
                sol_tx=sol_tx,
                neon_api_client=neon_api_client,
                evm_loader=evm_loader,
                operator_keypair=operator_keypair,
                done_simulation=done_simulation,
                done_execution=done_execution,
                simulated_compute_units=simulated_compute_units,
                actual_compute_units=actual_compute_units,
            )
            done = done_simulation and done_execution

        # Finish scheduled transaction steps (simulation and execution)
        finish_trx = instructions.TransactionWithComputeBudget(operator_keypair, compute_unit_price=1000000)
        finish_trx.add(
            instructions.make_ScheduledTransactionFinish(
                operator_keypair.pubkey(),
                operator_balance_pubkey,
                evm_loader.loader_id,
                holder_acc,
                tree_account,
            )
        )
        finish_trx.sign(operator_keypair)

        serialized_finish_transaction = finish_trx.serialize()
        hex_serialized_finish_transaction = serialized_finish_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()
        simulate_finish_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_finish_transaction],
        )
        simulated_finish_transactions = simulate_finish_response.json()["value"]["transactions"]
        simulated_compute_units += sum(
            [simulate_result["executed_units"] for simulate_result in simulated_finish_transactions]
        )

        finish_receipt = evm_loader.send_tx(finish_trx, operator_keypair)
        actual_compute_units += finish_receipt.value.transaction.meta.compute_units_consumed

        # Destroy tree account transaction steps (simulation and execution)
        destroy_trx = instructions.TransactionWithComputeBudget(operator_keypair)
        destroy_trx.add(
            instructions.make_ScheduledTransactionDestroy(
                signer=operator_keypair.pubkey(),
                balance_account=neon_user_balance_account,
                treasury=treasury_pool,
                tree_account=tree_account,
                evm_loader_id=evm_loader.loader_id,
            )
        )
        destroy_trx.sign(operator_keypair)

        serialized_destroy_transaction = destroy_trx.serialize()
        hex_serialized_destroy_transaction = serialized_destroy_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()
        simulate_destroy_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_destroy_transaction],
        )
        simulated_destroy_transactions = simulate_destroy_response.json()["value"]["transactions"]
        simulated_compute_units += sum(
            [simulate_result["executed_units"] for simulate_result in simulated_destroy_transactions]
        )

        destroy_receipt = evm_loader.send_tx(destroy_trx, operator_keypair)
        actual_compute_units += destroy_receipt.value.transaction.meta.compute_units_consumed

        # Compare simulation and execution results
        msg = f"Simulated: {simulated_compute_units}, executed: {actual_compute_units}"
        assert abs(simulated_compute_units - actual_compute_units) < 10, msg

    def test_simulate_solana_with_solana_overrides_data_account(
        self,
        solana_overrides_contract: Contract,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        def execute_trx(function_signature, params, additional_accounts):
            signed_tx = eth_utils.make_contract_call_trx(
                evm_loader=evm_loader,
                user=sender_with_tokens,
                contract=solana_overrides_contract,
                function_signature=function_signature,
                params=params,
            )

            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, additional_accounts
            )
            check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        update_b_function_signature = "update_b(uint256)"
        # value = 239 is hardcoded in solidity contract to be checked with check_b() method
        update_b_params = [239]

        emulate_result = neon_api_client.emulate_contract_call(
            sender=sender_with_tokens.eth_address.hex(),
            contract=solana_overrides_contract.eth_address.hex(),
            function_signature=update_b_function_signature,
            params=update_b_params,
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        execute_trx(update_b_function_signature, update_b_params, additional_accounts)

        accounts = [
            sender_with_tokens.balance_account_address,
            solana_overrides_contract.solana_address,
        ]
        data_account = list(set(additional_accounts) - set(accounts))[0]
        account_info_after_tx1 = evm_loader.get_account_info(data_account, commitment=Confirmed)

        execute_trx(update_b_function_signature, [192], additional_accounts)
        account_info_after_tx2 = evm_loader.get_account_info(data_account, commitment=Confirmed)

        assert account_info_after_tx1.value.data != account_info_after_tx2.value.data

        # Create Solana transaction
        signed_tx_for_sol_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=solana_overrides_contract,
            function_signature="check_b()",
        )
        sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_ExecuteTrxFromInstruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=signed_tx_for_sol_tx.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    solana_overrides_contract.solana_address,
                    data_account,
                ],
            )
        )
        sol_tx.sign(operator_keypair)

        # Simulate the transaction
        serialized_transaction = sol_tx.serialize()
        hex_serialized_transaction = serialized_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()

        account_info_override = {
            "lamports": account_info_after_tx1.value.lamports,
            "data": account_info_after_tx1.value.data.hex(),
            "owner": str(account_info_after_tx1.value.owner),
            "executable": account_info_after_tx1.value.executable,
            "rent_epoch": account_info_after_tx1.value.rent_epoch,
        }

        simulate_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_transaction],
            solana_overrides_params={str(data_account): account_info_override},
        )

        simulated_transactions = simulate_response.json()["value"]["transactions"]

        for simulated_transaction in simulated_transactions:
            if simulated_transaction["error"]:
                raise AssertionError(f"Error in sol trx: {simulated_transaction}")
            assert "Program log: exit_status=0x11" in simulated_transaction["logs"]

    def test_simulate_solana_with_solana_overrides_multiple_data_accounts(
        self,
        solana_overrides_contract: Contract,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        def execute_trx(function_signature, params, additional_accounts):
            signed_tx = eth_utils.make_contract_call_trx(
                evm_loader=evm_loader,
                user=sender_with_tokens,
                contract=solana_overrides_contract,
                function_signature=function_signature,
                params=params,
            )

            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, additional_accounts
            )
            check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        function_signature = "update_data(uint256,uint256)"
        # value = 123 is hardcoded in solidity contract to be checked with check_data(uint256) method
        params = [3, 123]

        emulate_result = neon_api_client.emulate_contract_call(
            sender=sender_with_tokens.eth_address.hex(),
            contract=solana_overrides_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        execute_trx(function_signature, params, additional_accounts)

        accounts = [
            sender_with_tokens.balance_account_address,
            solana_overrides_contract.solana_address,
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
        signed_tx_for_sol_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=solana_overrides_contract,
            function_signature="check_data(uint256)",
            params=[3],
        )
        sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_ExecuteTrxFromInstruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=signed_tx_for_sol_tx.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    solana_overrides_contract.solana_address,
                    data_accounts[0],
                    data_accounts[1],
                    data_accounts[2],
                ],
            )
        )
        sol_tx.sign(operator_keypair)

        # Simulate the transaction
        serialized_transaction = sol_tx.serialize()
        hex_serialized_transaction = serialized_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()

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

        simulate_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_transaction],
            solana_overrides_params=solana_overrides_params,
        )

        simulated_transactions = simulate_response.json()["value"]["transactions"]

        for simulated_transaction in simulated_transactions:
            if simulated_transaction["error"]:
                raise AssertionError(f"Error in sol trx: {simulated_transaction}")
            assert "Program log: exit_status=0x11" in simulated_transaction["logs"]

    def test_simulate_solana_with_solana_overrides_balance_account(
        self,
        solana_overrides_contract: Contract,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
        session_user: Caller,
    ):
        def execute_trx(function_signature, params, additional_accounts):
            signed_tx = eth_utils.make_contract_call_trx(
                evm_loader=evm_loader,
                user=sender_with_tokens,
                contract=solana_overrides_contract,
                function_signature=function_signature,
                params=params,
            )

            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, additional_accounts
            )
            check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        recipient = session_user
        recipient_balance_before = evm_loader.get_neon_balance(recipient.eth_address)
        balance_account = solana_overrides_contract.balance_account_address
        evm_loader.deposit_neon(operator_keypair, solana_overrides_contract.eth_address, 1000000)
        amount = evm_loader.get_neon_balance(solana_overrides_contract.eth_address)

        function_signature = "send_neon(address,uint256)"
        params = [recipient.eth_address.hex(), amount // 2]

        account_info_full_balance = evm_loader.get_account_info(balance_account, commitment=Confirmed)

        emulate_result = neon_api_client.emulate_contract_call(
            sender=sender_with_tokens.eth_address.hex(),
            contract=solana_overrides_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        execute_trx(function_signature, params, additional_accounts)

        recipient_balance_after = evm_loader.get_neon_balance(recipient.eth_address)
        assert recipient_balance_after == recipient_balance_before + amount // 2

        account_info_after_tx = evm_loader.get_account_info(balance_account, commitment=Confirmed)
        assert account_info_full_balance.value.data != account_info_after_tx.value.data

        contract_balance = evm_loader.get_neon_balance(solana_overrides_contract.eth_address)
        assert contract_balance < amount

        # Create Solana transaction
        signed_tx_for_sol_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=solana_overrides_contract,
            function_signature=function_signature,
            params=[recipient.eth_address.hex(), amount],
        )
        sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_ExecuteTrxFromInstruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=signed_tx_for_sol_tx.raw_transaction,
                additional_accounts=additional_accounts,
            )
        )
        sol_tx.sign(operator_keypair)

        # Simulate the transaction
        serialized_transaction = sol_tx.serialize()
        hex_serialized_transaction = serialized_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()

        account_info_override = {
            "lamports": account_info_full_balance.value.lamports,
            "data": account_info_full_balance.value.data.hex(),
            "owner": str(account_info_full_balance.value.owner),
            "executable": account_info_full_balance.value.executable,
            "rent_epoch": account_info_full_balance.value.rent_epoch,
        }

        simulate_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_transaction],
            solana_overrides_params={str(balance_account): account_info_override},
        )

        simulated_transactions = simulate_response.json()["value"]["transactions"]
        for simulated_transaction in simulated_transactions:
            if simulated_transaction["error"]:
                raise AssertionError(f"Error in sol trx: {simulated_transaction}")
            assert "Program log: exit_status=0x11" in simulated_transaction["logs"]

    def test_simulate_solana_with_solana_overrides_absent_field(
        self,
        solana_overrides_contract: Contract,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        function_signature = "update_b(uint256)"
        params = [4021]

        emulate_result = neon_api_client.emulate_contract_call(
            sender=sender_with_tokens.eth_address.hex(),
            contract=solana_overrides_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        signed_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=solana_overrides_contract,
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
            solana_overrides_contract.solana_address,
        ]
        data_account = list(set(additional_accounts) - set(accounts))[0]
        account_info = evm_loader.get_account_info(data_account, commitment=Confirmed)

        # Create Solana transaction
        signed_tx_for_sol_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=solana_overrides_contract,
            function_signature=function_signature,
            params=params,
        )
        sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_ExecuteTrxFromInstruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=signed_tx_for_sol_tx.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    solana_overrides_contract.solana_address,
                    data_account,
                ],
            )
        )
        sol_tx.sign(operator_keypair)

        # Simulate the transaction
        serialized_transaction = sol_tx.serialize()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()

        account_info_override = {
            "lamports": account_info.value.lamports,
            "data": account_info.value.data.hex(),
            "owner": str(account_info.value.owner),
            "executable": account_info.value.executable,
            "rent_epoch": account_info.value.rent_epoch,
        }
        keys = ["lamports", "data", "owner", "executable", "rent_epoch"]
        del account_info_override[random.SystemRandom().choice(keys)]

        simulate_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[serialized_transaction.hex()],
            solana_overrides_params={str(data_account): account_info_override},
        )
        assert simulate_response.status_code == 400
        assert "Json deserialize error: missing field" in simulate_response.text

    def test_simulate_solana_compare_cu_with_solana_overrides_and_without(
        self,
        solana_overrides_contract: Contract,
        sender_with_tokens: Caller,
        neon_api_client: NeonApiClient,
        operator_keypair: Keypair,
        evm_loader: EvmLoader,
        holder_acc: Pubkey,
        treasury_pool: TreasuryPool,
    ):
        def execute_trx(function_signature, params, additional_accounts):
            signed_tx = eth_utils.make_contract_call_trx(
                evm_loader=evm_loader,
                user=sender_with_tokens,
                contract=solana_overrides_contract,
                function_signature=function_signature,
                params=params,
            )

            evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
            resp = evm_loader.execute_transaction_steps_from_account(
                operator_keypair, treasury_pool, holder_acc, additional_accounts
            )
            check_transaction_logs_have_text(solana_client=evm_loader, trx=resp, text="exit_status=0x11")

        function_signature = "update_b(uint256)"
        params = [284]

        emulate_result = neon_api_client.emulate_contract_call(
            sender=sender_with_tokens.eth_address.hex(),
            contract=solana_overrides_contract.eth_address.hex(),
            function_signature=function_signature,
            params=params,
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        execute_trx(function_signature, params, additional_accounts)

        accounts = [
            sender_with_tokens.balance_account_address,
            solana_overrides_contract.solana_address,
        ]
        data_account = list(set(additional_accounts) - set(accounts))[0]
        account_info_after_tx1 = evm_loader.get_account_info(data_account, commitment=Confirmed)

        execute_trx(function_signature, [125], additional_accounts)

        # Create Solana transaction
        signed_tx_for_sol_tx = eth_utils.make_contract_call_trx(
            evm_loader=evm_loader,
            user=sender_with_tokens,
            contract=solana_overrides_contract,
            function_signature=function_signature,
            params=params,
        )
        sol_tx = instructions.TransactionWithComputeBudget(operator_keypair)
        operator_balance_pubkey = evm_loader.get_operator_balance_pubkey(operator_keypair)
        sol_tx.add(
            instructions.make_ExecuteTrxFromInstruction(
                operator=operator_keypair,
                operator_balance=operator_balance_pubkey,
                holder_address=holder_acc,
                evm_loader_id=evm_loader.loader_id,
                treasury_address=treasury_pool.account,
                treasury_buffer=treasury_pool.buffer,
                message=signed_tx_for_sol_tx.raw_transaction,
                additional_accounts=[
                    sender_with_tokens.balance_account_address,
                    solana_overrides_contract.solana_address,
                    data_account,
                ],
            )
        )
        sol_tx.sign(operator_keypair)

        # Simulate the transaction
        serialized_transaction = sol_tx.serialize()
        hex_serialized_transaction = serialized_transaction.hex()
        blockhash = base58.b58decode(str(evm_loader.get_latest_blockhash(Finalized).value.blockhash)).hex()

        account_info_override = {
            "lamports": account_info_after_tx1.value.lamports,
            "data": account_info_after_tx1.value.data.hex(),
            "owner": str(account_info_after_tx1.value.owner),
            "executable": account_info_after_tx1.value.executable,
            "rent_epoch": account_info_after_tx1.value.rent_epoch,
        }

        simulate_response_with_override = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_transaction],
            solana_overrides_params={str(data_account): account_info_override},
        )

        simulate_response = neon_api_client.simulate_solana(
            blockhash=blockhash,
            transactions=[hex_serialized_transaction],
        )

        simulated_tx = simulate_response.json()["value"]["transactions"][0]
        simulated_tx_with_overrides = simulate_response_with_override.json()["value"]["transactions"][0]

        assert simulated_tx["error"] is None
        assert "Program log: exit_status=0x11" in simulated_tx["logs"]
        assert simulated_tx_with_overrides["error"] is None
        assert "Program log: exit_status=0x11" in simulated_tx_with_overrides["logs"]
        assert simulated_tx_with_overrides["executed_units"] < simulated_tx["executed_units"]
