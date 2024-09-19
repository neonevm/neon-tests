from solana.transaction import Transaction

from utils.instructions import make_Cancel
from utils.layouts import FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT
from .utils.constants import TAG_FINALIZED_STATE
from .utils.contract import make_contract_call_trx
from .utils.storage import create_holder
from .utils.transaction_checks import check_holder_account_tag


#  We need test here two types of transaction
class TestCancelTrx:

    def test_cancel_trx(self, operator_keypair, rw_lock_contract, user_account, treasury_pool, evm_loader):
        """EVM can cancel transaction and finalize storage account"""
        signed_tx = make_contract_call_trx(evm_loader, user_account, rw_lock_contract, "unchange_storage(uint8,uint8)", [1, 1])

        storage_account = create_holder(operator_keypair, evm_loader)
        user_nonce_before_first_step = evm_loader.get_neon_nonce(user_account.eth_address)
        operator_balance = evm_loader.get_operator_balance_pubkey(operator_keypair)

        receipt = evm_loader.send_transaction_step_from_instruction(operator_keypair, operator_balance, treasury_pool, storage_account,
                                                     signed_tx,
                                                     [rw_lock_contract.solana_address,
                                                      rw_lock_contract.balance_account_address,
                                                      user_account.balance_account_address],
                                                     1, operator_keypair)

        assert receipt.value.transaction.meta.err is None

        user_nonce_after_first_step = evm_loader.get_neon_nonce(user_account.eth_address)
        assert user_nonce_before_first_step + 1 == user_nonce_after_first_step
        trx = Transaction()
        trx.add(
            make_Cancel(evm_loader.loader_id, storage_account, operator_keypair,operator_balance, signed_tx.hash,
                        [rw_lock_contract.solana_address,
                         rw_lock_contract.balance_account_address,
                         user_account.balance_account_address])
        )
        evm_loader.send_tx(trx, operator_keypair)
        check_holder_account_tag(storage_account, FINALIZED_STORAGE_ACCOUNT_INFO_LAYOUT, TAG_FINALIZED_STATE)
        assert user_nonce_after_first_step == evm_loader.get_neon_nonce(user_account.eth_address)
