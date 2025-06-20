import pytest

from solana.transaction import AccountMeta, Transaction, Instruction
from solana.rpc.commitment import Confirmed
from solders.system_program import ID as SYS_PROGRAM_ID
from solders.address_lookup_table_account import ID as ALT_PROGRAM_ID, derive_lookup_table_address

from utils.consts import ALT_UPDATER_ID
from utils.solana_client import SolanaClient
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client
from utils.solana_data_for_neon_trx_helper import get_alt_by_neon_trx, get_sol_account_list_by_neon_trx


@pytest.mark.usefixtures("accounts", "sol_client", "web3_client")
class TestAltUpdaterProgram:
    sol_client: SolanaClient
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    def test_execute_alt_updater_from_instruction(self, solana_account):
        slot = self.sol_client.get_slot().value

        # alt_address_0 = Pubkey.find_program_address(
        #     [
        #         bytes(solana_account.pubkey()),
        #         bytes([0x0]) + slot.to_bytes(8, "little"),
        #     ],
        #     ALT_PROGRAM_ID,
        # )[0]

        alt_address = derive_lookup_table_address(solana_account.pubkey(), slot)[0]

        instruction = Instruction(
            program_id=ALT_UPDATER_ID,
            accounts=[
                AccountMeta(pubkey=alt_address, is_signer=False, is_writable=False),
                AccountMeta(pubkey=solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=solana_account.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=ALT_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(pubkey=solana_account.pubkey(), is_signer=False, is_writable=True),
            ],
            data=bytes([0x0]) + slot.to_bytes(8, "little"),
        )

        trx = Transaction()
        trx.add(instruction)
        self.sol_client.send_tx_and_check_status_ok(trx, solana_account)

    def test_execute_alt_updater_alt_already_exists(self, alt_contract, operator_keypair, solana_account):
        sender_account = self.accounts[1]
        accounts_quantity = 59
        tx = self.web3_client.make_raw_tx(sender_account)

        instr = alt_contract.functions.fill(accounts_quantity).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instr)

        alt = get_alt_by_neon_trx(self.web3_client, self.sol_client, receipt["transactionHash"].hex())
        print(f"ALT acc after trx: {alt}")
        info = self.sol_client.get_account_info(pubkey=alt, commitment=Confirmed)
        print("ALT account info: ", info)
        print("Operator: ", operator_keypair.pubkey())
        sol_accounts = get_sol_account_list_by_neon_trx(
            self.web3_client, self.sol_client, receipt["transactionHash"].hex()
        )
        print(f"Sol account from trx: {sol_accounts}")
        slot = self.sol_client.get_slot().value

        instruction = Instruction(
            program_id=ALT_UPDATER_ID,
            accounts=[
                AccountMeta(alt, is_signer=False, is_writable=True),
                AccountMeta(sol_accounts[0], is_signer=False, is_writable=True),
                AccountMeta(operator_keypair.pubkey(), is_signer=True, is_writable=True),
                AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(ALT_PROGRAM_ID, is_signer=False, is_writable=False),
                AccountMeta(solana_account.pubkey(), is_signer=False, is_writable=True),
            ],
            data=bytes([0x0]) + slot.to_bytes(8, "little"),
        )

        trx = Transaction()
        trx.add(instruction)
        self.sol_client.send_tx_and_check_status_ok(trx, operator_keypair)
