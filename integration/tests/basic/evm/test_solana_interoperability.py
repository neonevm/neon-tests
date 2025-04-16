import typing as tp
import web3.exceptions
import random

import pytest
import spl
from solders.keypair import Keypair
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import AccountMeta, Instruction
from solders.pubkey import Pubkey
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    TransferParams,
    get_associated_token_address,
    transfer,
)

import allure
from utils.types import TransactionType
from utils.accounts import EthAccounts
from utils.consts import COUNTER_ID, TRANSFER_TOKENS_ID, wSOL
from utils.helpers import bytes32_to_solana_pubkey, serialize_instruction, wait_condition
from utils.instructions import make_wSOL
from utils.web3client import NeonChainWeb3Client


@pytest.fixture(scope="class")
def get_counter_value() -> tp.Iterator[int]:
    def gen_increment_counter():
        count = 0
        while True:
            count += 1
            yield count

    return gen_increment_counter()


@allure.feature("EVM tests")
@allure.story("Verify precompiled solana call contract")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client_session")
class TestSolanaInteroperability:
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    @pytest.fixture(scope="class")
    def call_solana_caller_sol_network(self, class_account_sol_chain, web3_client_sol):
        contract, _ = web3_client_sol.deploy_and_get_contract(
            contract="precompiled/CallSolanaCaller.sol",
            version="0.8.28",
            contract_name="CallSolanaCaller",
            account=class_account_sol_chain,
        )
        return contract

    def serialized_transfer(self, sol_client, from_wallet, to_wallet, amount, contract, is_set_authority=True):
        mint = spl.token.client.Token.create_mint(
            conn=sol_client,
            payer=from_wallet,
            mint_authority=from_wallet.pubkey(),
            decimals=9,
            program_id=TOKEN_PROGRAM_ID,
        )
        mint.payer = from_wallet
        from_token_account = mint.create_associated_token_account(from_wallet.pubkey())
        to_token_account = mint.create_associated_token_account(to_wallet.pubkey())
        mint.mint_to(
            dest=from_token_account,
            mint_authority=from_wallet,
            amount=amount,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        authority_pubkey: bytes = contract.functions.getSolanaPDA(bytes(TRANSFER_TOKENS_ID), b"authority").call()
        if is_set_authority:
            mint.set_authority(
                from_token_account,
                from_wallet,
                spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
                Pubkey(authority_pubkey),
                opts=TxOpts(skip_confirmation=False, skip_preflight=True),
            )

        instruction = Instruction(
            program_id=TRANSFER_TOKENS_ID,
            accounts=[
                AccountMeta(from_token_account, is_signer=False, is_writable=True),
                AccountMeta(mint.pubkey, is_signer=False, is_writable=True),
                AccountMeta(to_token_account, is_signer=False, is_writable=True),
                AccountMeta(Pubkey(authority_pubkey), is_signer=False, is_writable=True),
                AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
            data=bytes([0x0]),
        )
        return serialize_instruction(TRANSFER_TOKENS_ID, instruction), mint, [from_token_account, to_token_account]

    def test_counter_execute_with_get_return_data(
        self, call_solana_caller, counter_resource_address: bytes, get_counter_value
    ):
        sender = self.accounts[0]
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.executeWithGetReturnData(lamports, serialized).build_transaction(
            tx
        )

        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs = call_solana_caller.events.LogData().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == next(get_counter_value)
        assert bytes32_to_solana_pubkey(event_logs[0].args.program.hex()) == COUNTER_ID

    def test_transfer_with_pda_signature_iterative_tx_eip_1559(self, call_solana_caller, sol_client, solana_account):
        iterations = 20
        sender = self.accounts[0]
        from_wallet = solana_account
        to_wallet = Keypair()
        amount = 100000

        serialized, mint, accounts_list = self.serialized_transfer(
            sol_client, from_wallet, to_wallet, amount, call_solana_caller
        )
        tx = self.web3_client.make_raw_tx(
            from_=sender.address, amount=None, data=None, tx_type=TransactionType.EIP_1559
        )

        instruction_tx = call_solana_caller.functions.executeInIterativeMode(
            iterations, 0, serialized
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1
        assert resp.type == 2

        assert int(mint.get_balance(accounts_list[1], commitment=Confirmed).value.amount) == amount
        event_logs = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == 0

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(resp["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

    def test_counter_with_seed(self, call_solana_caller, counter_resource_address: bytes, get_counter_value):
        sender = self.accounts[0]
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        seed = self.web3_client.text_to_bytes32("myseed")
        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.executeWithSeed(lamports, seed, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == next(get_counter_value)

    def test_counter_execute(self, call_solana_caller, counter_resource_address: bytes, get_counter_value):
        sender = self.accounts[0]
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.execute(lamports, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == next(get_counter_value)

    def test_counter_batch_execute(self, call_solana_caller, counter_resource_address: bytes, get_counter_value):
        sender = self.accounts[0]
        call_params = []
        current_counter = 0

        for _ in range(10):
            instruction = Instruction(
                program_id=COUNTER_ID,
                accounts=[
                    AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
                ],
                data=bytes([0x1]),
            )
            serialized = serialize_instruction(COUNTER_ID, instruction)
            call_params.append((0, serialized))
            current_counter = next(get_counter_value)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.batchExecute(call_params).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs = call_solana_caller.events.LogData().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == current_counter
        assert bytes32_to_solana_pubkey(event_logs[0].args.program.hex()) == COUNTER_ID

    def test_transfer_with_pda_signature(self, call_solana_caller, sol_client, solana_account):
        sender = self.accounts[0]
        from_wallet = solana_account
        to_wallet = Keypair()
        amount = 100000

        mint = spl.token.client.Token.create_mint(
            conn=sol_client,
            payer=from_wallet,
            mint_authority=from_wallet.pubkey(),
            decimals=9,
            program_id=TOKEN_PROGRAM_ID,
        )
        mint.payer = from_wallet
        from_token_account = mint.create_associated_token_account(from_wallet.pubkey())
        to_token_account = mint.create_associated_token_account(to_wallet.pubkey())
        mint.mint_to(
            dest=from_token_account,
            mint_authority=from_wallet,
            amount=amount,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        authority_pubkey: bytes = call_solana_caller.functions.getSolanaPDA(
            bytes(TRANSFER_TOKENS_ID), b"authority"
        ).call()
        mint.set_authority(
            from_token_account,
            from_wallet,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            Pubkey(authority_pubkey),
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = Instruction(
            program_id=TRANSFER_TOKENS_ID,
            accounts=[
                AccountMeta(from_token_account, is_signer=False, is_writable=True),
                AccountMeta(mint.pubkey, is_signer=False, is_writable=True),
                AccountMeta(to_token_account, is_signer=False, is_writable=True),
                AccountMeta(Pubkey(authority_pubkey), is_signer=False, is_writable=True),
                AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
            data=bytes([0x0]),
        )
        serialized = serialize_instruction(TRANSFER_TOKENS_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.execute(0, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1
        assert int(mint.get_balance(to_token_account, commitment=Confirmed).value.amount) == amount
        event_logs = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == 0

    def test_transfer_tokens_with_ext_authority(self, call_solana_caller, sol_client, solana_account):
        sender = self.accounts[0]
        from_wallet = solana_account
        to_wallet = Keypair()
        amount = 100000

        mint = spl.token.client.Token.create_mint(
            conn=sol_client,
            payer=from_wallet,
            mint_authority=from_wallet.pubkey(),
            decimals=9,
            program_id=TOKEN_PROGRAM_ID,
        )
        mint.payer = from_wallet
        from_token_account = mint.create_associated_token_account(from_wallet.pubkey())
        to_token_account = mint.create_associated_token_account(to_wallet.pubkey())
        mint.mint_to(
            dest=from_token_account,
            mint_authority=from_wallet,
            amount=amount,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        seed = self.web3_client.text_to_bytes32("myseed")
        authority: bytes = call_solana_caller.functions.getExtAuthority(seed).call({"from": sender.address})

        mint.set_authority(
            from_token_account,
            from_wallet,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            Pubkey(authority),
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = transfer(
            TransferParams(TOKEN_PROGRAM_ID, from_token_account, to_token_account, Pubkey(authority), amount)
        )

        serialized = serialize_instruction(TOKEN_PROGRAM_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.executeWithSeed(0, seed, serialized).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1
        assert int(mint.get_balance(to_token_account, commitment=Confirmed).value.amount) == amount
        event_logs = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == 0

    def test_gas_estimate_for_wsol_transfer(self, new_solana_account, call_solana_caller, sol_client):
        sender = self.accounts[0]
        mint = wSOL["address_spl"]
        recipient = Keypair()

        spl_token = SplToken(sol_client, mint, TOKEN_PROGRAM_ID, new_solana_account)
        ata_address_from = get_associated_token_address(new_solana_account.pubkey(), mint)
        ata_address_to = get_associated_token_address(recipient.pubkey(), mint)
        sol_client.create_associate_token_acc(new_solana_account, new_solana_account, mint)
        sol_client.create_associate_token_acc(new_solana_account, recipient, mint)

        def get_gas_used_for_emulate_send_wsol(amount):
            wrap_sol_tx = make_wSOL(amount, new_solana_account.pubkey(), ata_address_from)
            sol_client.send_tx_and_check_status_ok(wrap_sol_tx, new_solana_account)
            seed = self.web3_client.text_to_bytes32("myseed")
            authority = call_solana_caller.functions.getExtAuthority(seed).call({"from": sender.address}).hex()
            authority = bytes32_to_solana_pubkey(authority)
            spl_token.set_authority(
                ata_address_from,
                new_solana_account,
                spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
                authority,
                opts=TxOpts(skip_confirmation=False, skip_preflight=True),
            )
            instr = transfer(TransferParams(TOKEN_PROGRAM_ID, ata_address_from, ata_address_to, authority, amount))
            serialized = serialize_instruction(TOKEN_PROGRAM_ID, instr)
            tx = self.web3_client.make_raw_tx(sender.address)
            instruction_tx = call_solana_caller.functions.batchExecuteWithSeed(
                [{"lamports": 0, "salt": seed, "instruction": serialized}]
            ).build_transaction(tx)
            signed_tx = self.web3_client.eth.account.sign_transaction(instruction_tx, sender.key)
            result = self.web3_client.get_neon_emulate(str(signed_tx.raw_transaction.hex()))
            resp = self.web3_client.eth.send_raw_transaction(signed_tx.raw_transaction)
            resp = self.web3_client.eth.wait_for_transaction_receipt(resp, timeout=60)
            assert resp["status"] == 1

            return result["result"]["gasUsed"]

        gas_used_amount1 = get_gas_used_for_emulate_send_wsol(10000)
        gas_used_amount2 = get_gas_used_for_emulate_send_wsol(10000 * 2)
        assert gas_used_amount1 == gas_used_amount2, "Gas used for different transfer amounts should be the same"

    def test_limit_of_simple_instr_in_one_trx(self, call_solana_caller, counter_resource_address: bytes):
        sender = self.accounts[0]
        call_params = []

        for _ in range(30):
            instruction = Instruction(
                program_id=COUNTER_ID,
                accounts=[
                    AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
                ],
                data=bytes([0x1]),
            )
            serialized = serialize_instruction(COUNTER_ID, instruction)
            call_params.append((0, serialized))

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.batchExecute(call_params).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 0, resp

    def test_solana_call_after_iterative_actions_sol_network(
        self,
        web3_client_sol,
        counter_resource_address: bytes,
        call_solana_caller_sol_network,
        get_counter_value,
        class_account_sol_chain,
    ):
        iterations = 29
        sender = class_account_sol_chain
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = web3_client_sol.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller_sol_network.functions.executeInIterativeMode(
            iterations, lamports, serialized
        ).build_transaction(tx)
        resp = web3_client_sol.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs = call_solana_caller_sol_network.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == next(get_counter_value)

    def test_solana_call_after_iterative_actions(
        self, counter_resource_address: bytes, call_solana_caller, get_counter_value
    ):
        sender = self.accounts[0]
        lamports = 0
        matrix_length = 9
        matrix = [[random.randint(1, 100) for _ in range(matrix_length)] for _ in range(matrix_length)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.solanaCallAfterActionWithMatrix(
            matrix, lamports, serialized
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs_bytes = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs_bytes[0].args.value, byteorder="little") == next(get_counter_value)
        event_logs_int = call_solana_caller.events.LogInt().process_receipt(resp)
        assert event_logs_int[0].args.value == sum(sum(row) for row in matrix)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(resp["transactionHash"].hex()) is True,
            timeout_sec=60,
        )

    def test_solana_call_after_iterative_actions_evm_memory_limit(
        self, counter_resource_address: bytes, call_solana_caller
    ):
        sender = self.accounts[0]
        lamports = 0
        matrix_length = 70
        matrix = [[random.randint(1, 100) for _ in range(matrix_length)] for _ in range(matrix_length)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)

        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="out of limits",
        ):
            call_solana_caller.functions.solanaCallAfterActionWithMatrix(
                matrix, lamports, serialized
            ).build_transaction(tx)

    def test_failed_solana_call_after_iterative_actions(self, call_solana_caller, sol_client, solana_account):
        iterations = 29
        sender = self.accounts[0]
        from_wallet = solana_account
        to_wallet = Keypair()
        amount = 100000

        serialized, _, _ = self.serialized_transfer(
            sol_client, from_wallet, to_wallet, amount, call_solana_caller, False
        )

        tx = self.web3_client.make_raw_tx(from_=sender.address, estimate_gas=True)

        instruction_tx = call_solana_caller.functions.executeInIterativeMode(
            iterations, 0, serialized
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 0

        event_logs = call_solana_caller.events.LogStr().process_receipt(resp)
        assert len(event_logs) == 0

    @pytest.mark.only_stands  #  This doesn't work on devnet
    def test_solana_call_after_iterative_actions_exceed_accounts_limit(
        self, counter_resource_address: bytes, call_solana_caller
    ):
        loop_count = 64
        sender = self.accounts[0]
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)

        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="too many accounts",
        ):
            call_solana_caller.functions.executeInIterativeMode(loop_count, lamports, serialized).build_transaction(tx)

    def test_solana_call_inside_iterative_actions(
        self, counter_resource_address: bytes, call_solana_caller, get_counter_value
    ):
        sender = self.accounts[0]
        lamports = 0
        matrix_length = 8
        matrix = [[random.randint(1, 100) for _ in range(matrix_length)] for _ in range(matrix_length)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.solanaCallInsideActionWithMatrix(
            matrix, lamports, serialized
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs_bytes = call_solana_caller.events.LogBytes().process_receipt(resp)
        for i in range(matrix_length - 1):
            next(get_counter_value)

        all_logs_value = [
            int.from_bytes(event_logs_byte.args.value, byteorder="little") for event_logs_byte in event_logs_bytes
        ]

        assert max(all_logs_value) == next(get_counter_value)

        event_logs_int = call_solana_caller.events.LogInt().process_receipt(resp)
        assert event_logs_int[0].args.value == sum(sum(row) for row in matrix)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(resp["transactionHash"].hex()) is True,
            timeout_sec=60,
        )

    def test_solana_call_of_two_programs_in_one_iterative_tx(
        self, counter_resource_address: bytes, call_solana_caller, get_counter_value, sol_client, solana_account
    ):
        iterations = 10
        sender = self.accounts[0]
        from_wallet = solana_account
        to_wallet = Keypair()
        amount = 100000

        serialized_transfer, mint, accounts_list = self.serialized_transfer(
            sol_client, from_wallet, to_wallet, amount, call_solana_caller
        )

        tx = self.web3_client.make_raw_tx(sender.address)

        instruction_counter = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized_counter = serialize_instruction(COUNTER_ID, instruction_counter)

        instruction_tx = call_solana_caller.functions.batchExecuteInIterativeMode(
            iterations, [(0, serialized_transfer), (0, serialized_counter)]
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender, instruction_tx)
        wait_condition(
            lambda: self.web3_client.is_trx_iterative(resp["transactionHash"].hex()) is True,
            timeout_sec=120,
        )
        assert resp["status"] == 1
        assert int(mint.get_balance(accounts_list[1], commitment=Confirmed).value.amount) == amount

        event_logs_data = call_solana_caller.events.LogData().process_receipt(resp)
        assert int.from_bytes(event_logs_data[0].args.value, byteorder="little") == next(get_counter_value)
        assert bytes32_to_solana_pubkey(event_logs_data[0].args.program.hex()) == COUNTER_ID

    def test_solana_call_before_iterative_actions(
        self, counter_resource_address: bytes, call_solana_caller, get_counter_value
    ):
        sender = self.accounts[0]
        lamports = 0
        matrix_lenght = 6
        matrix = [[random.randint(1, 100) for _ in range(matrix_lenght)] for _ in range(matrix_lenght)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.solanaCallBeforeActionWithMatrix(
            matrix, lamports, serialized
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs_bytes = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs_bytes[0].args.value, byteorder="little") == next(get_counter_value)
        event_logs_int = call_solana_caller.events.LogInt().process_receipt(resp)
        assert event_logs_int[0].args.value == sum(sum(row) for row in matrix)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(resp["transactionHash"].hex()) is True,
            timeout_sec=60,
        )

    def test_solana_call_before_iterative_actions_negative(self, counter_resource_address: bytes, call_solana_caller):
        sender = self.accounts[0]
        lamports = 0
        matrix_lenght = 15
        matrix = [[random.randint(1, 100) for _ in range(matrix_lenght)] for _ in range(matrix_lenght)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)

        instruction_tx = call_solana_caller.functions.solanaCallBeforeActionWithMatrix(
            matrix, lamports, serialized
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 0, resp

    def test_iterative_actions_and_multiple_solana_calls(
        self, counter_resource_address: bytes, call_solana_caller, get_counter_value
    ):
        iterations = 20
        solana_calls = 5
        lamports = 0

        current_counter = 0
        call_params = []

        sender = self.accounts[0]

        for _ in range(solana_calls):
            instruction = Instruction(
                program_id=COUNTER_ID,
                accounts=[
                    AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
                ],
                data=bytes([0x1]),
            )
            serialized = serialize_instruction(COUNTER_ID, instruction)
            call_params.append((lamports, serialized))
            current_counter = next(get_counter_value)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.batchExecuteInIterativeMode(
            iterations, call_params
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs_data = call_solana_caller.events.LogData().process_receipt(resp)
        assert int.from_bytes(event_logs_data[0].args.value, byteorder="little") == current_counter
        assert bytes32_to_solana_pubkey(event_logs_data[0].args.program.hex()) == COUNTER_ID

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(resp["transactionHash"].hex()) is True,
            timeout_sec=60,
        )

    def test_deploy_contract_and_call_solana(
        self, counter_resource_address: bytes, call_solana_caller, get_counter_value
    ):
        sender = self.accounts[0]
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.deployStorageAndCallSolana(
            lamports, serialized
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs_bytes = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs_bytes[0].args.value, byteorder="little") == next(get_counter_value)
        event_logs_address = call_solana_caller.events.LogAddress().process_receipt(resp)
        assert event_logs_address[0].args.value is not None

    def test_iterative_tx_with_send_tokens(
        self, counter_resource_address: bytes, call_solana_caller, get_counter_value
    ):
        iterations = 29
        sender = self.accounts[0]
        lamports = 0
        balance_before = self.web3_client.get_balance(call_solana_caller.address)

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(from_=sender.address, amount=10)

        instruction_tx = call_solana_caller.functions.sendTokensAndExecuteInIterativeMode(
            iterations, lamports, serialized
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1

        event_logs = call_solana_caller.events.LogBytes().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == next(get_counter_value)

        balance_after = self.web3_client.get_balance(call_solana_caller.address)
        assert balance_after == balance_before + 10
