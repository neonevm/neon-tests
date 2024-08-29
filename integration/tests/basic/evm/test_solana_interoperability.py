import pytest
import spl
from solana.keypair import Keypair
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from solana.transaction import AccountMeta, TransactionInstruction
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (
    TransferParams,
    get_associated_token_address,
    transfer,
)

import allure
from utils.accounts import EthAccounts
from utils.consts import COUNTER_ID, TRANSFER_TOKENS_ID, wSOL
from utils.helpers import bytes32_to_solana_pubkey, serialize_instruction
from utils.instructions import make_wSOL
from utils.web3client import NeonChainWeb3Client


@pytest.fixture(scope="session")
def get_counter_value():
    def gen_increment_counter():
        count = 0
        while True:
            count += 1
            yield count

    return gen_increment_counter()


@pytest.mark.proxy_version("v1.12.0")
@allure.feature("EVM tests")
@allure.story("Verify precompiled solana call contract")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client_session")
class TestSolanaInteroperability:
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    def test_counter_execute_with_get_return_data(
        self, call_solana_caller, counter_resource_address, get_counter_value
    ):
        sender = self.accounts[0]
        lamports = 0

        instruction = TransactionInstruction(
            program_id=COUNTER_ID,
            keys=[
                AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.execute_with_get_return_data(
            lamports, serialized
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 1
        event_logs = call_solana_caller.events.LogData().process_receipt(resp)
        assert int.from_bytes(event_logs[0].args.value, byteorder="little") == next(get_counter_value)
        assert bytes32_to_solana_pubkey(event_logs[0].args.program.hex()) == COUNTER_ID

    def test_counter_with_seed(self, call_solana_caller, counter_resource_address, get_counter_value):
        sender = self.accounts[0]
        lamports = 0

        instruction = TransactionInstruction(
            program_id=COUNTER_ID,
            keys=[
                AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
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

    def test_counter_execute(self, call_solana_caller, counter_resource_address, get_counter_value):
        sender = self.accounts[0]
        lamports = 0

        instruction = TransactionInstruction(
            program_id=COUNTER_ID,
            keys=[
                AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
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

    def test_counter_batch_execute(self, call_solana_caller, counter_resource_address, get_counter_value):
        sender = self.accounts[0]
        call_params = []
        current_counter = 0

        for _ in range(10):
            instruction = TransactionInstruction(
                program_id=COUNTER_ID,
                keys=[
                    AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
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

    def test_transfer_with_pda_signature(
        self, call_solana_caller, sol_client, solana_account, pytestconfig, bank_account
    ):
        sender = self.accounts[0]
        from_wallet = Keypair.generate()
        to_wallet = Keypair.generate()
        amount = 100000
        if pytestconfig.environment.use_bank:
            sol_client.send_sol(bank_account, from_wallet.public_key, int(0.5 * 10**9))
        else:
            sol_client.request_airdrop(from_wallet.public_key, 1000 * 10**9, commitment=Confirmed)

        mint = spl.token.client.Token.create_mint(
            conn=sol_client,
            payer=from_wallet,
            mint_authority=from_wallet.public_key,
            decimals=9,
            program_id=TOKEN_PROGRAM_ID,
        )
        mint.payer = from_wallet
        from_token_account = mint.create_associated_token_account(from_wallet.public_key)
        to_token_account = mint.create_associated_token_account(to_wallet.public_key)
        mint.mint_to(
            dest=from_token_account,
            mint_authority=from_wallet,
            amount=amount,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        authority_pubkey = call_solana_caller.functions.getSolanaPDA(bytes(TRANSFER_TOKENS_ID), b"authority").call()
        mint.set_authority(
            from_token_account,
            from_wallet,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            authority_pubkey,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = TransactionInstruction(
            program_id=TRANSFER_TOKENS_ID,
            keys=[
                AccountMeta(from_token_account, is_signer=False, is_writable=True),
                AccountMeta(mint.pubkey, is_signer=False, is_writable=True),
                AccountMeta(to_token_account, is_signer=False, is_writable=True),
                AccountMeta(authority_pubkey, is_signer=False, is_writable=True),
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

    def test_transfer_tokens_with_ext_authority(self, call_solana_caller, sol_client, pytestconfig, bank_account):
        sender = self.accounts[0]
        from_wallet = Keypair.generate()
        to_wallet = Keypair.generate()
        amount = 100000
        if pytestconfig.environment.use_bank:
            sol_client.send_sol(bank_account, from_wallet.public_key, int(0.5 * 10**9))
        else:
            sol_client.request_airdrop(from_wallet.public_key, 1000 * 10**9, commitment=Confirmed)
        mint = spl.token.client.Token.create_mint(
            conn=sol_client,
            payer=from_wallet,
            mint_authority=from_wallet.public_key,
            decimals=9,
            program_id=TOKEN_PROGRAM_ID,
        )
        mint.payer = from_wallet
        from_token_account = mint.create_associated_token_account(from_wallet.public_key)
        to_token_account = mint.create_associated_token_account(to_wallet.public_key)
        mint.mint_to(
            dest=from_token_account,
            mint_authority=from_wallet,
            amount=amount,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        seed = self.web3_client.text_to_bytes32("myseed")
        authority = call_solana_caller.functions.getExtAuthority(seed).call({"from": sender.address})

        mint.set_authority(
            from_token_account,
            from_wallet,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            authority,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = transfer(
            TransferParams(TOKEN_PROGRAM_ID, from_token_account, to_token_account, authority, amount)
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
        recipient = Keypair.generate()

        spl_token = SplToken(sol_client, mint, TOKEN_PROGRAM_ID, new_solana_account)
        ata_address_from = get_associated_token_address(new_solana_account.public_key, mint)
        ata_address_to = get_associated_token_address(recipient.public_key, mint)
        sol_client.create_associate_token_acc(new_solana_account, new_solana_account, mint)
        sol_client.create_associate_token_acc(new_solana_account, recipient, mint)

        def get_gas_used_for_emulate_send_wsol(amount):
            wrap_sol_tx = make_wSOL(amount, new_solana_account.public_key, ata_address_from)
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
            result = self.web3_client.get_neon_emulate(str(signed_tx.rawTransaction.hex())[2:])
            resp = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
            resp = self.web3_client.eth.wait_for_transaction_receipt(resp, timeout=60)
            assert resp["status"] == 1
            return result["result"]["gasUsed"]

        gas_used_amount1 = get_gas_used_for_emulate_send_wsol(10000)
        gas_used_amount2 = get_gas_used_for_emulate_send_wsol(10000 * 2)
        assert gas_used_amount1 == gas_used_amount2, "Gas used for different transfer amounts should be the same"

    def test_limit_of_simple_instr_in_one_trx(self, call_solana_caller, counter_resource_address):
        sender = self.accounts[0]
        call_params = []

        for _ in range(24):
            instruction = TransactionInstruction(
                program_id=COUNTER_ID,
                keys=[
                    AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
                ],
                data=bytes([0x1]),
            )
            serialized = serialize_instruction(COUNTER_ID, instruction)
            call_params.append((0, serialized))

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.batchExecute(call_params).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 0

