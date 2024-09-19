import random

import eth_abi
import pytest

from eth_utils import abi
from eth_keys import keys as eth_keys
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed
from solana.rpc.core import RPCException
from solana.rpc.types import TxOpts
import spl.token.client
from spl.token.client import Token
from solders.system_program import ID as SYS_PROGRAM_ID
from solana.transaction import Instruction, AccountMeta
from spl.token.instructions import create_associated_token_account, TransferParams, transfer


from integration.tests.neon_evm.utils.call_solana import SolanaCaller


from integration.tests.neon_evm.utils.constants import NEON_TOKEN_MINT_ID
from integration.tests.neon_evm.utils.contract import deploy_contract, make_contract_call_trx

from integration.tests.neon_evm.utils.ethereum import make_eth_transaction

from utils.consts import (
    MEMO_PROGRAM_ID,
    COMPUTE_BUDGET_ID,
    SOLANA_CALL_PRECOMPILED_ID,
    COUNTER_ID,
    TRANSFER_SOL_ID,
    TRANSFER_TOKENS_ID,
)

from integration.tests.neon_evm.utils.transaction_checks import check_transaction_logs_have_text, decode_logs
from utils.evm_loader import EvmLoader, CHAIN_ID
from utils.helpers import serialize_instruction

from utils.instructions import DEFAULT_UNITS, make_CreateAssociatedTokenIdempotent
from utils.layouts import COUNTER_ACCOUNT_LAYOUT
from utils.metaplex import ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID, TOKEN_PROGRAM_ID
from utils.types import Caller


def _create_mint_and_accounts(evm_loader, from_wallet, to_wallet, amount) -> tuple[Token, Pubkey, Pubkey]:
    mint = spl.token.client.Token.create_mint(
        conn=evm_loader,
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
    return mint, from_token_account, to_token_account


class TestInteroperability:
    @pytest.fixture(scope="function")
    def solana_caller(
        self, evm_loader: EvmLoader, operator_keypair: Keypair, session_user: Caller, treasury_pool, holder_acc
    ) -> SolanaCaller:
        return SolanaCaller(operator_keypair, session_user, evm_loader, treasury_pool, holder_acc)

    def test_get_solana_address_by_neon_address(self, sender_with_tokens, solana_caller):
        sol_addr = solana_caller.get_solana_address_by_neon_address(sender_with_tokens.eth_address.hex())
        assert sol_addr == sender_with_tokens.solana_account_address

    def test_get_payer(self, solana_caller):
        assert solana_caller.get_payer() != ""

    def test_get_solana_PDA(self, solana_caller):
        addr = solana_caller.get_solana_PDA(COUNTER_ID, b"123")
        assert addr == (Pubkey.find_program_address([b"123"], COUNTER_ID))[0]

    def test_get_eth_ext_authority(self, solana_caller, sender_with_tokens):
        addr = solana_caller.get_eth_ext_authority(b"123", sender_with_tokens)
        assert addr != ""

    def test_create_resource(self, sender_with_tokens, solana_caller, evm_loader):
        salt = b"123"
        size = 8
        resource_address = solana_caller.create_resource(sender_with_tokens, salt, size, 1000000000, MEMO_PROGRAM_ID)
        acc_info = evm_loader.get_account_info(resource_address, commitment=Confirmed)
        assert acc_info.value is not None
        assert acc_info.value.lamports > 0
        assert len(acc_info.value.data) == size
        assert str(acc_info.value.owner) == str(MEMO_PROGRAM_ID)

    def test_execute_from_instruction_for_compute_budget(self, sender_with_tokens, solana_caller):
        instruction = Instruction(
            program_id=COMPUTE_BUDGET_ID,
            accounts=[AccountMeta(sender_with_tokens.solana_account_address, is_signer=False, is_writable=False)],
            data=bytes.fromhex("02") + DEFAULT_UNITS.to_bytes(4, "little"),
        )
        resp = solana_caller.execute(COMPUTE_BUDGET_ID, instruction, sender=sender_with_tokens)
        check_transaction_logs_have_text(resp, "exit_status=0x11")

    def test_execute_from_instruction_for_call_memo(
        self, sender_with_tokens, neon_api_client, operator_keypair, evm_loader, treasury_pool, sol_client, holder_acc
    ):
        contract = deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "precompiled/call_solana_test",
            evm_loader,
            treasury_pool,
            contract_name="Test",
        )

        data = abi.function_signature_to_4byte_selector("call_memo()")
        signed_tx = make_eth_transaction(evm_loader, contract.eth_address, data, sender_with_tokens)

        resp = evm_loader.execute_trx_from_instruction_with_solana_call(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                SOLANA_CALL_PRECOMPILED_ID,
                MEMO_PROGRAM_ID,
                contract.balance_account_address,
                contract.solana_address,
            ],
        )
        check_transaction_logs_have_text(resp, "exit_status=0x11")

    def test_execute_from_account_create_acc(self, sender_with_tokens, solana_caller, evm_loader):
        payer = solana_caller.get_payer()
        instruction = make_CreateAssociatedTokenIdempotent(
            payer, sender_with_tokens.solana_account_address, NEON_TOKEN_MINT_ID
        )
        resp = solana_caller.batch_execute(
            [(ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID, 2039280, instruction)], sender_with_tokens
        )
        check_transaction_logs_have_text(resp, "exit_status=0x11")
        payer_info = evm_loader.get_account_info(payer, commitment=Confirmed)
        assert payer_info.value is None

    def test_execute_several_instr_in_one_trx(self, sender_with_tokens, solana_caller, evm_loader):
        instruction_count = 10
        resource_addr = solana_caller.create_resource(sender_with_tokens, b"123", 8, 1000000000, COUNTER_ID)

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(resource_addr, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        call_params = []
        for i in range(instruction_count):
            call_params.append((COUNTER_ID, 0, instruction))

        resp = solana_caller.batch_execute(call_params, sender_with_tokens)

        check_transaction_logs_have_text(resp, "exit_status=0x11")
        info: bytes = evm_loader.get_solana_account_data(resource_addr, COUNTER_ACCOUNT_LAYOUT.sizeof())
        layout = COUNTER_ACCOUNT_LAYOUT.parse(info)
        assert layout.count == instruction_count

    def test_limit_of_simple_instr_in_one_trx(self, sender_with_tokens, solana_caller):
        instruction_count = 24
        resource_addr = solana_caller.create_resource(sender_with_tokens, b"123", 8, 1000000000, COUNTER_ID)

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(resource_addr, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        call_params = []
        for i in range(instruction_count):
            call_params.append((COUNTER_ID, 0, instruction))

        with pytest.raises(
            RPCException, match=r"failed: exceeded CUs meter at BPF instruction|Computational budget exceeded"
        ):
            solana_caller.batch_execute(call_params, sender_with_tokens)

    def test_transfer_sol_with_cpi(self, sender_with_tokens, solana_caller, evm_loader):
        recipient = evm_loader.create_account(sender_with_tokens.solana_account, 0, TRANSFER_SOL_ID)
        amount = random.randint(1, 1000000)
        instruction = Instruction(
            program_id=TRANSFER_SOL_ID,
            accounts=[
                AccountMeta(sender_with_tokens.solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(recipient.pubkey(), is_signer=False, is_writable=True),
                AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
            data=bytes([0x0]) + amount.to_bytes(8, "little"),
        )
        call_params = [(TRANSFER_SOL_ID, 0, instruction)]
        balance_before = evm_loader.get_balance(recipient.pubkey(), commitment=Confirmed).value
        resp = solana_caller.batch_execute(
            call_params, sender_with_tokens, additional_signers=[sender_with_tokens.solana_account]
        )
        check_transaction_logs_have_text(resp, "exit_status=0x11")
        balance_after = evm_loader.get_balance(recipient.pubkey(), commitment=Confirmed).value
        assert balance_after == balance_before + amount

    def test_transfer_sol_without_cpi(self, solana_caller, sender_with_tokens, evm_loader):
        amount = random.randint(1, 1000000)
        sender = evm_loader.create_account(
            sender_with_tokens.solana_account, 0, TRANSFER_SOL_ID, lamports=100 * 10**9
        )
        recipient = evm_loader.create_account(sender_with_tokens.solana_account, 0, TRANSFER_SOL_ID)

        instruction = Instruction(
            program_id=TRANSFER_SOL_ID,
            accounts=[
                AccountMeta(sender.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(recipient.pubkey(), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]) + amount.to_bytes(8, "little"),
        )
        call_params = [(TRANSFER_SOL_ID, 0, instruction)]
        balance_before = evm_loader.get_balance(recipient.pubkey(), Confirmed).value
        resp = solana_caller.batch_execute(call_params, sender_with_tokens, additional_signers=[sender])
        balance_after = evm_loader.get_balance(recipient.pubkey(), Confirmed).value
        check_transaction_logs_have_text(resp, "exit_status=0x11")
        assert balance_after == balance_before + amount

    def test_transfer_with_PDA_signature(self, solana_caller, sender_with_tokens, evm_loader):
        from_wallet = Keypair()
        to_wallet = Keypair()
        amount = 100000
        evm_loader.request_airdrop(from_wallet.pubkey(), 1000 * 10**9, commitment=Confirmed)

        mint, from_token_account, to_token_account = _create_mint_and_accounts(
            evm_loader, from_wallet, to_wallet, amount
        )

        authority_pubkey = solana_caller.get_solana_PDA(TRANSFER_TOKENS_ID, b"authority")
        mint.set_authority(
            from_token_account,
            from_wallet,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            authority_pubkey,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = Instruction(
            program_id=TRANSFER_TOKENS_ID,
            accounts=[
                AccountMeta(from_token_account, is_signer=False, is_writable=True),
                AccountMeta(mint.pubkey, is_signer=False, is_writable=True),
                AccountMeta(to_token_account, is_signer=False, is_writable=True),
                AccountMeta(authority_pubkey, is_signer=False, is_writable=True),
                AccountMeta(TOKEN_PROGRAM_ID, is_signer=False, is_writable=True),
            ],
            data=bytes([0x0]),
        )

        resp = solana_caller.execute(TRANSFER_TOKENS_ID, instruction, sender=sender_with_tokens)
        check_transaction_logs_have_text(resp, "exit_status=0x11")
        assert int(mint.get_balance(to_token_account, commitment=Confirmed).value.amount) == amount

    def test_transfer_tokens_with_ext_authority(self, evm_loader, sender_with_tokens, solana_caller):
        from_wallet = sender_with_tokens
        to_wallet = Keypair()
        amount = 100000
        mint, from_token_account, to_token_account = _create_mint_and_accounts(
            evm_loader, from_wallet.solana_account, to_wallet, amount
        )
        seed = b"myseed"
        authority = solana_caller.get_eth_ext_authority(seed, from_wallet)

        mint.set_authority(
            from_token_account,
            from_wallet.solana_account,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            authority,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = transfer(
            TransferParams(TOKEN_PROGRAM_ID, from_token_account, to_token_account, authority, amount)
        )

        resp = solana_caller.execute_with_seed(TOKEN_PROGRAM_ID, instruction, seed, sender=from_wallet)
        check_transaction_logs_have_text(resp, "exit_status=0x11")

        assert int(mint.get_balance(to_token_account, commitment=Confirmed).value.amount) == amount

    def test_transfer_tokens_with_unauthorized_signer(self, solana_caller, sender_with_tokens, evm_loader):
        from_wallet = sender_with_tokens
        to_wallet = Keypair()
        amount = 100000
        mint, from_token_account, to_token_account = _create_mint_and_accounts(
            evm_loader, from_wallet.solana_account, to_wallet, amount
        )

        authority = solana_caller.get_eth_ext_authority(b"myseed", from_wallet)

        mint.set_authority(
            from_token_account,
            from_wallet.solana_account,
            spl.token.instructions.AuthorityType.ACCOUNT_OWNER,
            authority,
            opts=TxOpts(skip_confirmation=False, skip_preflight=True),
        )

        instruction = transfer(
            TransferParams(TOKEN_PROGRAM_ID, from_token_account, to_token_account, authority, amount)
        )
        with pytest.raises(RPCException, match="Cross-program invocation with unauthorized signer or writable account"):
            solana_caller.execute(TOKEN_PROGRAM_ID, instruction, sender=from_wallet)

    def test_staticcall_does_not_support_external_call(
        self, sender_with_tokens, solana_caller, operator_keypair, evm_loader, treasury_pool, holder_acc
    ):
        precompiled_caller = deploy_contract(
            operator_keypair,
            sender_with_tokens,
            "precompiled/CommonCaller",
            evm_loader,
            treasury_pool,
            contract_name="CommonCaller",
            version="0.8.3",
        )

        resource_addr = solana_caller.create_resource(sender_with_tokens, b"123", 8, 1000000000, COUNTER_ID)

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(resource_addr, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )

        serialized_instructions = serialize_instruction(COUNTER_ID, instruction)
        calldata = abi.function_signature_to_4byte_selector("execute(uint64,bytes)") + eth_abi.encode(
            ["uint64", "bytes"], [1000000000, serialized_instructions]
        )

        signed_tx = make_contract_call_trx(
            evm_loader,
            sender_with_tokens,
            precompiled_caller,
            "staticcall_precompiled(address,bytes)",
            [solana_caller.contract.eth_address, calldata],
        )

        try:
            resp = evm_loader.execute_trx_from_instruction_with_solana_call(
                operator_keypair,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    sender_with_tokens.solana_account_address,
                    SOLANA_CALL_PRECOMPILED_ID,
                    solana_caller.contract.balance_account_address,
                    solana_caller.contract.solana_address,
                    precompiled_caller.balance_account_address,
                    precompiled_caller.solana_address,
                    COUNTER_ID,
                    resource_addr,
                ],
            )
        except RPCException as err:
            assert "static mode violation" in decode_logs(err.args[0].data.logs)
        else:
            assert False, f"Expected error but got {resp}"

    def test_call_neon_instruction_by_neon_instruction(
        self,
        sender_with_tokens,
        solana_caller,
        operator_keypair,
        evm_loader,
        treasury_pool,
        new_holder_acc,
    ):
        key = Keypair()
        caller_ether = eth_keys.PrivateKey(key.secret()[:32]).public_key.to_canonical_address()

        account_pubkey = evm_loader.ether2balance(caller_ether)
        contract_pubkey = Pubkey.from_string(evm_loader.ether2program(caller_ether)[0])

        data = bytes([0x30]) + evm_loader.ether2bytes(caller_ether) + CHAIN_ID.to_bytes(8, "little")
        neon_instruction = Instruction(
            program_id=evm_loader.loader_id,
            data=data,
            accounts=[
                AccountMeta(pubkey=sender_with_tokens.solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=account_pubkey, is_signer=False, is_writable=True),
                AccountMeta(pubkey=contract_pubkey, is_signer=False, is_writable=True),
            ],
        )

        try:
            resp = solana_caller.batch_execute(
                [
                    (evm_loader.loader_id, 0, neon_instruction),
                ],
                sender_with_tokens,
                additional_signers=[sender_with_tokens.solana_account],
            )
        except RPCException as err:
            assert "Program not allowed to call itself" in decode_logs(err.args[0].data.logs)
        else:
            assert False, f"Expected error but got {resp}"
