import pytest

from solana.transaction import AccountMeta, Transaction, Instruction
from solders.keypair import Keypair
from solana.rpc.commitment import Confirmed
from solders.system_program import ID as SYS_PROGRAM_ID
from solders.address_lookup_table_account import ID as SYS_ALT_PROGRAM_ID, derive_lookup_table_address

from utils.consts import ALT_UPDATER_ID
from utils.solana_client import SolanaClient
from integration.tests.neon_evm.utils.transaction_checks import (
    check_transaction_logs_have_text,
    check_transaction_logs_have_not_text,
)


@pytest.mark.usefixtures("sol_client")
class TestAltUpdaterProgram:
    sol_client: SolanaClient

    def test_alt_updater_create_alt(self, solana_account):
        slot = self.sol_client.get_slot().value

        alt_address = derive_lookup_table_address(solana_account.pubkey(), slot)[0]
        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value is None

        instruction = Instruction(
            program_id=ALT_UPDATER_ID,
            accounts=[
                AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
                AccountMeta(pubkey=solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYS_ALT_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
            data=slot.to_bytes(8, "little"),
        )

        trx = Transaction()
        trx.add(instruction)
        receipt = self.sol_client.send_tx_and_check_status_ok(trx, solana_account)

        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value.owner == SYS_ALT_PROGRAM_ID
        assert alt_info.value.data is not None

        check_transaction_logs_have_text(self.sol_client, receipt, "Instruction: CreateLookupTable")
        check_transaction_logs_have_not_text(self.sol_client, receipt, "Instruction: ExtendLookupTable")

    def test_alt_updater_create_alt_and_extend(self, solana_account):
        new_account = Keypair()
        slot = self.sol_client.get_slot().value

        alt_address = derive_lookup_table_address(solana_account.pubkey(), slot)[0]
        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value is None

        instruction = Instruction(
            program_id=ALT_UPDATER_ID,
            accounts=[
                AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
                AccountMeta(pubkey=solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYS_ALT_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=new_account.pubkey(), is_signer=False, is_writable=True),
            ],
            data=slot.to_bytes(8, "little"),
        )

        trx = Transaction()
        trx.add(instruction)
        receipt = self.sol_client.send_tx_and_check_status_ok(trx, solana_account)

        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value.owner == SYS_ALT_PROGRAM_ID
        assert alt_info.value.data is not None

        check_transaction_logs_have_text(self.sol_client, receipt, "Instruction: CreateLookupTable")
        check_transaction_logs_have_text(self.sol_client, receipt, "Instruction: ExtendLookupTable")

    def test_alt_updater_extend_existing_non_empty_alt(self, solana_account):
        new_account_0 = Keypair()
        slot = self.sol_client.get_slot().value

        alt_address = derive_lookup_table_address(solana_account.pubkey(), slot)[0]
        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value is None

        accounts = [
            AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=solana_account.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYS_ALT_PROGRAM_ID, is_signer=False, is_writable=False),
            AccountMeta(pubkey=new_account_0.pubkey(), is_signer=False, is_writable=True),
        ]

        instruction = Instruction(
            program_id=ALT_UPDATER_ID,
            accounts=accounts,
            data=slot.to_bytes(8, "little"),
        )

        trx = Transaction()
        trx.add(instruction)
        receipt = self.sol_client.send_tx_and_check_status_ok(trx, solana_account)

        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value.owner == SYS_ALT_PROGRAM_ID
        assert alt_info.value.data is not None

        check_transaction_logs_have_text(self.sol_client, receipt, "Instruction: CreateLookupTable")
        check_transaction_logs_have_text(self.sol_client, receipt, "Instruction: ExtendLookupTable")

        new_account_1 = Keypair()
        accounts[4] = AccountMeta(pubkey=new_account_1.pubkey(), is_signer=False, is_writable=True)
        for _ in range(9):
            new_account = Keypair()
            accounts.append(AccountMeta(pubkey=new_account.pubkey(), is_signer=False, is_writable=True))
        instruction.accounts = accounts

        trx = Transaction()
        trx.add(instruction)
        receipt = self.sol_client.send_tx_and_check_status_ok(trx, solana_account)

        alt_info_upd = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info_upd.value.owner == SYS_ALT_PROGRAM_ID
        assert alt_info_upd.value.data is not None
        assert alt_info_upd.value.data != alt_info.value.data

        check_transaction_logs_have_text(self.sol_client, receipt, "Instruction: ExtendLookupTable")
        check_transaction_logs_have_not_text(self.sol_client, receipt, "Instruction: CreateLookupTable")

    def test_alt_updater_create_same_alt_twice(self, solana_account):
        slot = self.sol_client.get_slot().value

        alt_address = derive_lookup_table_address(solana_account.pubkey(), slot)[0]
        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value is None

        instruction = Instruction(
            program_id=ALT_UPDATER_ID,
            accounts=[
                AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
                AccountMeta(pubkey=solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYS_ALT_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
            data=slot.to_bytes(8, "little"),
        )

        trx = Transaction()
        trx.add(instruction)
        receipt = self.sol_client.send_tx_and_check_status_ok(trx, solana_account)

        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value.owner == SYS_ALT_PROGRAM_ID
        assert alt_info.value.data is not None

        check_transaction_logs_have_text(self.sol_client, receipt, "Instruction: CreateLookupTable")
        check_transaction_logs_have_not_text(self.sol_client, receipt, "Instruction: ExtendLookupTable")

        receipt_alt_unchanged = self.sol_client.send_tx_and_check_status_ok(trx, solana_account)
        alt_info_unchanged = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info_unchanged.value.owner == SYS_ALT_PROGRAM_ID
        assert alt_info_unchanged.value.data == alt_info.value.data

        check_transaction_logs_have_not_text(self.sol_client, receipt_alt_unchanged, "Instruction: CreateLookupTable")
        check_transaction_logs_have_not_text(self.sol_client, receipt_alt_unchanged, "Instruction: ExtendLookupTable")

    def test_alt_updater_invalid_insrtuction_data_size_mismatch(self, solana_account):
        slot = self.sol_client.get_slot().value

        alt_address = derive_lookup_table_address(solana_account.pubkey(), slot)[0]
        alt_info = self.sol_client.get_account_info(alt_address, commitment=Confirmed)
        assert alt_info.value is None

        instruction = Instruction(
            program_id=ALT_UPDATER_ID,
            accounts=[
                AccountMeta(pubkey=alt_address, is_signer=False, is_writable=True),
                AccountMeta(pubkey=solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=SYS_ALT_PROGRAM_ID, is_signer=False, is_writable=False),
            ],
            data=slot.to_bytes(4, "little"),
        )

        trx = Transaction()
        trx.add(instruction)
        with pytest.raises(AssertionError, match=f"Program {ALT_UPDATER_ID} failed: invalid instruction data"):
            self.sol_client.send_tx_and_check_status_ok(trx, solana_account)
