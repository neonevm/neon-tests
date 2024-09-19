import random
import string

import pytest
import eth_abi
from eth_account.datastructures import SignedTransaction
from eth_keys import keys as eth_keys
from eth_utils import abi, to_text
from hexbytes import HexBytes
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.core import RPCException as SolanaRPCException
from spl.token.instructions import get_associated_token_address

from utils.types import Caller, Contract
from .utils.assert_messages import InstructionAsserts
from .utils.constants import NEON_TOKEN_MINT_ID
from .utils.contract import make_contract_call_trx
from .utils.ethereum import make_eth_transaction
from .utils.storage import create_holder
from .utils.transaction_checks import check_transaction_logs_have_text


class TestExecuteTrxFromInstruction:
    def test_simple_transfer_transaction(
        self, operator_keypair, treasury_pool, sender_with_tokens: Caller, session_user: Caller, evm_loader, holder_acc
    ):
        amount = 10

        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        recipient_balance_before = evm_loader.get_neon_balance(session_user.eth_address)

        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, amount)
        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
        )
        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        recipient_balance_after = evm_loader.get_neon_balance(session_user.eth_address)
        assert sender_balance_before - amount == sender_balance_after
        assert recipient_balance_before + amount == recipient_balance_after
        check_transaction_logs_have_text(resp, "exit_status=0x11")

    def test_transfer_transaction_with_non_existing_recipient(
        self, operator_keypair, treasury_pool, sender_with_tokens: Caller, evm_loader, holder_acc
    ):
        # recipient account should be created
        recipient = Keypair()

        recipient_ether = eth_keys.PrivateKey(recipient.secret()[:32]).public_key.to_canonical_address()
        recipient_solana_address, _ = evm_loader.ether2program(recipient_ether)
        recipient_balance_address = evm_loader.ether2balance(recipient_ether)
        amount = 10
        signed_tx = make_eth_transaction(evm_loader, recipient_ether, None, sender_with_tokens, amount)
        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                recipient_balance_address,
                Pubkey.from_string(recipient_solana_address),
            ],
        )

        recipient_balance_after = evm_loader.get_neon_balance(recipient_ether)
        check_transaction_logs_have_text(resp, "exit_status=0x11")

        assert recipient_balance_after == amount

    def test_call_contract_function_without_neon_transfer(
        self,
        operator_keypair,
        treasury_pool,
        sender_with_tokens: Caller,
        string_setter_contract: Contract,
        evm_loader,
        neon_api_client,
        holder_acc
    ):
        text = "".join(random.choice(string.ascii_letters) for _ in range(10))
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, string_setter_contract, "set(string)", [text]
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [sender_with_tokens.balance_account_address, string_setter_contract.solana_address],
        )

        check_transaction_logs_have_text(resp, "exit_status=0x11")
        assert text in to_text(
            neon_api_client.call_contract_get_function(sender_with_tokens, string_setter_contract, "get()")
        )

    def test_call_contract_function_with_neon_transfer(
        self,
        operator_keypair,
        treasury_pool,
        sender_with_tokens: Caller,
        evm_loader,
        neon_api_client,
        string_setter_contract,
        holder_acc
    ):
        transfer_amount = random.randint(1, 1000)

        sender_balance_before = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        contract_balance_before = evm_loader.get_neon_balance(string_setter_contract.eth_address)

        text = "".join(random.choice(string.ascii_letters) for _ in range(10))
        func_name = abi.function_signature_to_4byte_selector("set(string)")
        data = func_name + eth_abi.encode(["string"], [text])
        signed_tx = make_eth_transaction(
            evm_loader, string_setter_contract.eth_address, data, sender_with_tokens, transfer_amount
        )
        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                string_setter_contract.balance_account_address,
                string_setter_contract.solana_address,
            ],
        )

        check_transaction_logs_have_text(resp, "exit_status=0x11")

        assert text in to_text(
            neon_api_client.call_contract_get_function(sender_with_tokens, string_setter_contract, "get()")
        )

        sender_balance_after = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        contract_balance_after = evm_loader.get_neon_balance(string_setter_contract.eth_address)
        assert sender_balance_before - transfer_amount == sender_balance_after
        assert contract_balance_before + transfer_amount == contract_balance_after

    def test_incorrect_chain_id(
        self, operator_keypair, treasury_pool, sender_with_tokens: Caller, session_user: Caller, evm_loader, holder_acc
    ):
        amount = 1
        signed_tx = make_eth_transaction(
            evm_loader, session_user.eth_address, None, sender_with_tokens, amount, chain_id=1
        )
        with pytest.raises(SolanaRPCException, match=InstructionAsserts.INVALID_CHAIN_ID):
            evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
            )

    def test_incorrect_nonce(
        self, operator_keypair, treasury_pool, sender_with_tokens: Caller, session_user: Caller, evm_loader, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)

        evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
        )
        with pytest.raises(SolanaRPCException, match=InstructionAsserts.INVALID_NONCE):
            evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
            )

    def test_insufficient_funds(
        self, operator_keypair, treasury_pool, evm_loader, sender_with_tokens: Caller, session_user: Caller, holder_acc
    ):
        user_balance = evm_loader.get_neon_balance(session_user.eth_address)

        signed_tx = make_eth_transaction(
            evm_loader, sender_with_tokens.eth_address, None, session_user, user_balance + 1
        )

        with pytest.raises(SolanaRPCException, match=InstructionAsserts.INSUFFICIENT_FUNDS):
            evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
                operator_keypair,
            )

    def test_gas_limit_reached(
        self, operator_keypair, treasury_pool, session_user: Caller, sender_with_tokens: Caller, evm_loader, holder_acc
    ):
        amount = 10
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, amount, gas=1)

        with pytest.raises(SolanaRPCException, match=InstructionAsserts.OUT_OF_GAS):
            evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
            )

    def test_sender_missed_in_remaining_accounts(
        self, operator_keypair, treasury_pool, session_user: Caller, sender_with_tokens: Caller, evm_loader, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        with pytest.raises(SolanaRPCException, match=InstructionAsserts.ADDRESS_MUST_BE_PRESENT):
            evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [session_user.balance_account_address, session_user.solana_account_address],
            )

    def test_recipient_missed_in_remaining_accounts(
        self, operator_keypair, treasury_pool, sender_with_tokens: Caller, session_user: Caller, evm_loader, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        with pytest.raises(SolanaRPCException, match=InstructionAsserts.ADDRESS_MUST_BE_PRESENT):
            evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [sender_with_tokens.balance_account_address],
            )

    def test_incorrect_treasure_pool(
        self, operator_keypair, sender_with_tokens: Caller, session_user: Caller, evm_loader, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)

        treasury_buffer = b"\x02\x00\x00\x00"
        treasury_pool = Keypair().pubkey()

        error = str.format(InstructionAsserts.INVALID_ACCOUNT, treasury_pool)
        with pytest.raises(SolanaRPCException, match=error):
            evm_loader.execute_trx_from_instruction(operator_keypair, holder_acc, treasury_pool, treasury_buffer, signed_tx, [])

    def test_incorrect_treasure_index(
        self, operator_keypair, treasury_pool, sender_with_tokens: Caller, session_user: Caller, evm_loader, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        treasury_buffer = b"\x03\x00\x00\x00"

        error = str.format(InstructionAsserts.INVALID_ACCOUNT, treasury_pool.account)
        with pytest.raises(SolanaRPCException, match=error):
            evm_loader.execute_trx_from_instruction(
                operator_keypair, holder_acc, treasury_pool.account, treasury_buffer, signed_tx, []
            )

    def test_incorrect_operator_account(
        self, evm_loader, treasury_pool, session_user: Caller, sender_with_tokens: Caller, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        fake_operator = Keypair()
        with pytest.raises(SolanaRPCException, match=InstructionAsserts.ACC_NOT_FOUND):
            evm_loader.execute_trx_from_instruction(
                fake_operator,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
            )

    def test_operator_is_not_in_white_list(self, sender_with_tokens, evm_loader, treasury_pool, session_user, holder_acc):
        # check any user can send transactions through "execute transaction from instruction" instruction with own holder

        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        holder_acc = create_holder(sender_with_tokens.solana_account, evm_loader)

        resp = evm_loader.execute_trx_from_instruction(
            sender_with_tokens.solana_account,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                session_user.balance_account_address,
                session_user.solana_account_address,
            ],
            sender_with_tokens.solana_account,
        )
        check_transaction_logs_have_text(resp, "exit_status=0x11")

    def test_incorrect_system_program(
        self, sender_with_tokens, operator_keypair, evm_loader, treasury_pool, session_user, holder_acc
    ):
        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        fake_sys_program_id = Keypair().pubkey()
        with pytest.raises(
            SolanaRPCException, match=str.format(InstructionAsserts.NOT_SYSTEM_PROGRAM, fake_sys_program_id)
        ):
            evm_loader.execute_trx_from_instruction(
                operator_keypair,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [],
                operator_keypair,
                system_program=fake_sys_program_id,
            )

    def test_operator_does_not_have_enough_founds(
        self, evm_loader, treasury_pool, session_user: Caller, sender_with_tokens: Caller, operator_keypair, holder_acc
    ):
        key = Keypair()
        caller_ether = eth_keys.PrivateKey(key.secret()[:32]).public_key.to_canonical_address()
        caller, caller_nonce = evm_loader.ether2program(caller_ether)
        caller_token = get_associated_token_address(Pubkey.from_string(caller), NEON_TOKEN_MINT_ID)

        operator_without_money = Caller(key, Pubkey.from_string(caller), caller_ether, caller_nonce, caller_token)

        signed_tx = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, 1)
        with pytest.raises(
            SolanaRPCException, match="Attempt to debit an account but found no record of a prior credit"
        ):
            evm_loader.execute_trx_from_instruction(
                operator_without_money.solana_account,
                holder_acc,
                treasury_pool.account,
                treasury_pool.buffer,
                signed_tx,
                [
                    sender_with_tokens.balance_account_address,
                    session_user.balance_account_address,
                    session_user.solana_account_address,
                ],
                operator_without_money.solana_account,
            )

    def test_transaction_with_access_list(
        self,
        operator_keypair,
        holder_acc,
        treasury_pool,
        sender_with_tokens,
        evm_loader,
        calculator_contract,
        calculator_caller_contract,
    ):
        access_list = (
            {
                "address": "0x" + calculator_contract.eth_address.hex(),
                "storageKeys": (
                    "0x0000000000000000000000000000000000000000000000000000000000000000",
                    "0x0000000000000000000000000000000000000000000000000000000000000001",
                ),
            },
        )
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, calculator_caller_contract, "callCalculator()", access_list=access_list
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx,
            [
                sender_with_tokens.balance_account_address,
                calculator_caller_contract.solana_address,
                calculator_contract.solana_address,
            ],
            operator_keypair,
        )

        check_transaction_logs_have_text(resp, "exit_status=0x12")

    def test_old_trx_type_with_leading_zeros(
        self,
        sender_with_tokens,
        operator_keypair,
        evm_loader,
        calculator_caller_contract,
        calculator_contract,
        treasury_pool,
        holder_acc,
    ):
        signed_tx = make_contract_call_trx(
            evm_loader, sender_with_tokens, calculator_caller_contract, "callCalculator()"
        )
        new_raw_trx = HexBytes(bytes([0]) + signed_tx.rawTransaction)

        signed_tx_new = SignedTransaction(
            rawTransaction=new_raw_trx,
            hash=signed_tx.hash,
            r=signed_tx.r,
            s=signed_tx.s,
            v=signed_tx.v,
        )

        resp = evm_loader.execute_trx_from_instruction(
            operator_keypair,
            holder_acc,
            treasury_pool.account,
            treasury_pool.buffer,
            signed_tx_new,
            [
                sender_with_tokens.balance_account_address,
                calculator_caller_contract.solana_address,
                calculator_contract.solana_address,
            ],
        )
        check_transaction_logs_have_text(resp, "exit_status=0x12")
