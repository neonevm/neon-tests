from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.constants import TAG_FINALIZED_STATE
from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.transaction_checks import (
    check_holder_account_tag,
    check_transaction_logs_have_text,
)
from utils.evm_loader import EVM_STEPS
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from utils.types import Contract


class TestAccountList:

    def test_all_accounts_sent_in_last_iteration(
        self, session_user, evm_loader, operator_keypair, treasury_pool, holder_acc, neon_api_client, sol_client
    ):

        contract: Contract = evm_loader.deploy_contract(
            operator=operator_keypair,
            user=session_user,
            contract_file_name="neon_evm/out_of_contract_scope.sol",
            neon_api_client=neon_api_client,
            treasury_pool=treasury_pool,
            contract_name="SaveNumber",
            version="0.8.12",
        )

        signed_tx = make_contract_call_trx(evm_loader, session_user, contract, "saveNumberToVar(uint256)", params=[5])
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        emulate_result = neon_api_client.emulate_contract_call(
            session_user.eth_address.hex(), contract.eth_address.hex(), "saveNumberToVar(uint256)", params=[5]
        )

        acc_from_emulation = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        signed_tx = make_contract_call_trx(evm_loader, session_user, contract, "saveNumberToVar(uint256)", params=[5])
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)

        # First iteration
        for i in range(2):
            evm_loader.send_transaction_step_from_account(
                operator=operator_keypair,
                operator_balance_pubkey=operator_balance,
                treasury=treasury_pool,
                storage_account=holder_acc,
                additional_accounts=[contract.solana_address, session_user.balance_account_address],
                steps_count=1,
                signer=operator_keypair,
            )

        evm_loader.send_transaction_step_from_account(
            operator=operator_keypair,
            operator_balance_pubkey=operator_balance,
            treasury=treasury_pool,
            storage_account=holder_acc,
            additional_accounts=acc_from_emulation,
            steps_count=EVM_STEPS,
            signer=operator_keypair,
        )

        trx_final = evm_loader.send_transaction_step_from_account(
            operator=operator_keypair,
            operator_balance_pubkey=operator_balance,
            treasury=treasury_pool,
            storage_account=holder_acc,
            additional_accounts=acc_from_emulation,
            steps_count=EVM_STEPS,
            signer=operator_keypair,
        )

        check_holder_account_tag(
            solana_client=sol_client,
            storage_account=holder_acc,
            layout=FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT,
            expected_tag=TAG_FINALIZED_STATE,
        )

        check_transaction_logs_have_text(solana_client=sol_client, trx=trx_final, text="exit_status=0x11")

    def test_account_list_with_blockhash(
        self, evm_loader, session_user, operator_keypair, treasury_pool, holder_acc, neon_api_client, sol_client
    ):
        contract: Contract = evm_loader.deploy_contract(
            operator=operator_keypair,
            user=session_user,
            contract_file_name="opcodes/BlockHash.sol",
            neon_api_client=neon_api_client,
            treasury_pool=treasury_pool,
            contract_name="BlockHashTest",
            version="0.8.10",
        )
        slot = evm_loader.get_slot().value
        signed_tx = make_contract_call_trx(evm_loader, session_user, contract, "getValues(uint256)", params=[slot])
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        emulate_result = neon_api_client.emulate_contract_call(
            session_user.eth_address.hex(), contract.eth_address.hex(), "getValues(uint256)", params=[slot]
        )
        acc_from_emulation = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        assert Pubkey.from_string("SysvarS1otHashes111111111111111111111111111") not in acc_from_emulation
        resp = evm_loader.execute_transaction_steps_from_account(
            operator_keypair, treasury_pool, holder_acc, acc_from_emulation
        )
        check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x12")
