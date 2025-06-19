import pytest

from solana.transaction import AccountMeta, Transaction, Instruction
from solders.system_program import ID as SYS_PROGRAM_ID
from solders.address_lookup_table_account import ID as ALT_PROGRAM_ID

from utils.consts import ALT_UPDATER_ID
from utils.solana_client import SolanaClient


@pytest.mark.usefixtures("sol_client")
class TestAltUpdaterProgram:
    sol_client: SolanaClient

    def test_execute_alt_updater_from_instruction(self, operator_keypair, evm_loader, sender_with_tokens, session_user):
        slot = evm_loader.get_slot().value
        alt_account = evm_loader.make_new_user(operator_keypair)

        instruction = Instruction(
            program_id=ALT_UPDATER_ID,
            accounts=[
                AccountMeta(alt_account.solana_account.pubkey(), is_signer=False, is_writable=True),
                AccountMeta(sender_with_tokens.solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(sender_with_tokens.solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(ALT_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(session_user.solana_account.pubkey(), is_signer=False, is_writable=True),
            ],
            data=bytes([0x0]) + slot.to_bytes(8, "little"),
        )

        trx = Transaction()
        trx.add(instruction)
        self.sol_client.send_tx_and_check_status_ok(trx, sender_with_tokens.solana_account)
