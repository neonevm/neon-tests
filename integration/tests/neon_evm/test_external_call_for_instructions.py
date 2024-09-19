import pytest
from solana.rpc.core import RPCException
from solana.transaction import AccountMeta, Transaction, Instruction

from utils.consts import TEST_INVOKE_ID
from utils.instructions import (
    TransactionWithComputeBudget,
    make_ExecuteTrxFromInstruction,
)
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client

from .utils.ethereum import make_eth_transaction


@pytest.mark.usefixtures("sol_client", "web3_client")
class TestExternalCall:
    sol_client: SolanaClient
    web3_client: NeonChainWeb3Client

    def test_execute_from_instruction(
        self, operator_keypair, evm_loader, treasury_pool, sender_with_tokens, session_user, holder_acc
    ):
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
        amount = 1

        msg = make_eth_transaction(evm_loader, session_user.eth_address, None, sender_with_tokens, amount)
        accounts = [
            sender_with_tokens.solana_account_address,
            sender_with_tokens.balance_account_address,
            session_user.solana_account_address,
            session_user.balance_account_address,
        ]

        sender_initial_balance = evm_loader.get_neon_balance(sender_with_tokens.eth_address)
        receiver_initial_balance = evm_loader.get_neon_balance(session_user.eth_address)

        instruction = make_ExecuteTrxFromInstruction(
            operator_keypair,
            operator_balance,
            holder_acc,
            evm_loader.loader_id,
            treasury_pool.account,
            treasury_pool.buffer,
            msg.rawTransaction,
            accounts,
        )
        upd_instruction = Instruction(
            accounts=[AccountMeta(evm_loader.loader_id, is_signer=False, is_writable=True)] + instruction.accounts,
            program_id=TEST_INVOKE_ID,
            data=instruction.data,
        )
        trx = Transaction()

        trx.add(upd_instruction)
        self.sol_client.send_tx(trx, operator_keypair)

        assert sender_initial_balance == evm_loader.get_neon_balance(sender_with_tokens.eth_address) + amount
        assert receiver_initial_balance == evm_loader.get_neon_balance(session_user.eth_address) - amount

    def test_execute_from_instruction_eip_1559(
        self, operator_keypair, evm_loader, treasury_pool, sender_with_tokens, session_user, holder_acc
    ):
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)
        amount = 1
        compute_unit_price = 1000000
        max_fee_per_gas = 100
        max_priority_fee_per_gas = 10

        msg = make_eth_transaction(
            evm_loader,
            session_user.eth_address,
            None,
            sender_with_tokens,
            amount,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas
        )

        accounts = [
            sender_with_tokens.solana_account_address,
            sender_with_tokens.balance_account_address,
            session_user.solana_account_address,
            session_user.balance_account_address,
        ]

        instruction = make_ExecuteTrxFromInstruction(
            operator_keypair,
            operator_balance,
            holder_acc,
            evm_loader.loader_id,
            treasury_pool.account,
            treasury_pool.buffer,
            msg.rawTransaction,
            accounts,
        )
        upd_instruction = Instruction(
            accounts=[AccountMeta(evm_loader.loader_id, is_signer=False, is_writable=True)] + instruction.accounts,
            program_id=TEST_INVOKE_ID,
            data=instruction.data,
        )
        trx = TransactionWithComputeBudget(operator_keypair, compute_unit_price)
        trx.add(upd_instruction)
        with pytest.raises(RPCException, match="CPI calls of Neon EVM are forbidden for DynamicFee transaction type"):
            self.sol_client.send_tx(trx, operator_keypair)
