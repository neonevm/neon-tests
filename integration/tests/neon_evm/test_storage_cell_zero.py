import pytest
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.ethereum import make_contract_call_trx
from integration.tests.neon_evm.utils.neon_api_client import NeonApiClient
from utils.evm_loader import EvmLoader
from utils.types import Contract, Caller, TreasuryPool


@pytest.mark.parametrize(
    "function_signature",
    [
        "saveZeroToVar()",
        "saveZeroToMapping()",
        "saveZeroToMappingCycle()",
    ],
)
class TestStorageCells:
    def test_save_zero(
        self,
        operator_keypair: Keypair,
        session_user: Caller,
        evm_loader: EvmLoader,
        treasury_pool: TreasuryPool,
        neon_api_client: NeonApiClient,
        holder_acc: Pubkey,
        function_signature: str,
    ):
        # Deploy the contract
        contract: Contract = evm_loader.deploy_contract(
            operator=operator_keypair,
            user=session_user,
            contract_file_name="neon_evm/store_zeros.sol",
            neon_api_client=neon_api_client,
            treasury_pool=treasury_pool,
            contract_name="saveZeros",
            version="0.8.12",
        )

        # Emulate contract function call transaction
        emulate_accounts = neon_api_client.get_additional_accounts_by_emulation(
            sender=session_user.eth_address.hex(),
            contract=contract.eth_address.hex(),
            function_signature=function_signature,
        )

        # Define the storage accounts
        non_storage_accounts = (contract.solana_address, session_user.balance_account_address)
        storage_accounts = [acc for acc in emulate_accounts if acc not in non_storage_accounts]

        # Actually execute the transaction
        signed_tx = make_contract_call_trx(
            evm_loader=evm_loader, user=session_user, contract=contract, function_signature=function_signature
        )
        evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

        evm_loader.execute_transaction_steps_from_account(
            operator=operator_keypair,
            treasury=treasury_pool,
            storage_account=holder_acc,
            additional_accounts=emulate_accounts,
        )

        # Make sure the emulated storage accounts were not actually created (have 0 balance)
        for storage_account in storage_accounts:
            balance = evm_loader.get_solana_balance(storage_account)
            assert balance == 0, f"Account {storage_account} was created"
