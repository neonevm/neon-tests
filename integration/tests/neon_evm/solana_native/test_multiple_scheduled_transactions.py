import os

import eth_abi
import pytest
import solana
from eth_utils import abi
from solders.pubkey import Pubkey

from integration.tests.neon_evm.utils.assert_messages import InstructionAsserts
from integration.tests.neon_evm.utils.contract import get_contract_bin
from integration.tests.neon_evm.utils.ethereum import create_contract_address
from integration.tests.neon_evm.utils.storage import create_holder
from integration.tests.neon_evm.utils.constants import SOL_CHAIN_ID, SOL_MINT_ID
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData
from utils.types import Contract


class TestMultipleScheduledTrx:
    # ┌───────┐  ┌──────┐
    # │ t0 ✓  ├─>┤ t1 ✓ │
    # │ s=0   │  │ s=1  │
    # └───────┘  └──────┘
    def test_2_depended_transactions(
        self, neon_user, basic_contract, evm_loader, treasury_pool, holder_acc, operator_keypair, neon_api_client
    ):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx0 = ScheduledTransaction(
            neon_user.neon_address, None, nonce, index=0, target=basic_contract.eth_address, call_data=data
        )
        tx1 = ScheduledTransaction(
            neon_user.neon_address, None, nonce, index=1, target=basic_contract.eth_address, call_data=data
        )
        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(tx0, 1, 0)
        tree_acc_data.add_trx(tx1, 0xFFFF, 1)
        print(tree_acc_data.data)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, SOL_MINT_ID
        )
        additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(SOL_CHAIN_ID)]
        print(tree_account)
        evm_loader.execute_scheduled_trx_from_instruction(
            tx0, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )

        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)

        holder_acc2 = create_holder(operator_keypair, evm_loader)
        evm_loader.execute_scheduled_trx_from_instruction(
            tx1, operator_keypair, holder_acc2, tree_account, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc2)
        evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_account)
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).transactions == []

    # ┌───────┐  ┌──────┐
    # │ t0 x  ├─>┤ t1 ✓ │
    # │ s=0   │  │ s=1  │
    # └───────┘  └──────┘
    def test_2_depended_transactions_one_failed(
        self, neon_user, basic_contract, evm_loader, treasury_pool, holder_acc, operator_keypair, neon_api_client
    ):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        tx0 = ScheduledTransaction(
            neon_user.neon_address, None, nonce, index=0, target=basic_contract.eth_address, value=0
        )
        tx1 = ScheduledTransaction(
            neon_user.neon_address, None, nonce, index=1, target=basic_contract.eth_address, value=0, call_data=data
        )
        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(tx0, 1, 0)
        tree_acc_data.add_trx(tx1, 0xFFFF, 1)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, SOL_MINT_ID
        )
        emulate_result = neon_api_client.emulate(
            neon_user.neon_address.hex(), basic_contract.eth_address.hex(), data.hex(), chain_id=SOL_CHAIN_ID
        )
        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
        evm_loader.execute_scheduled_trx_from_instruction(
            tx0, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)

        with pytest.raises(solana.rpc.core.RPCException,
                           match=InstructionAsserts.TRANSACTION_TREE_INVALID_SUCCESS_LIMIT):
            evm_loader.execute_scheduled_trx_from_instruction(
                tx1, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
            )

        evm_loader.skip_scheduled_trx_from_instruction(tx1, operator_keypair, tree_account, holder_acc)
        tree_account_data = neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce)
        assert tree_account_data.transactions[0].is_failed()
        assert tree_account_data.transactions[1].is_skipped()
        evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_account)
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).transactions == []

    #  ┌──────┐
    #  │ t0 ✓ │
    # ─┤ s=1  ├─┐
    #  └──────┘ │
    #  ┌──────┐ │ ┌──────┐
    # ─┤ t1 ✓ ├─┼>┤ t3 ✓ │
    #  │ s=1  │ │ │ s=0  │
    #  └──────┘ │ └──────┘
    #  ┌──────┐ │
    # ─┤ t2 ✓ ├─┘
    #  │ s=1  │
    #  └──────┘
    def test_tree_with_parallel_trx(
        self, evm_loader, neon_user, basic_contract, treasury_pool, holder_acc, operator_keypair, neon_api_client
    ):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_data = 18
        data = abi.function_signature_to_4byte_selector("setNumber(uint256)") + eth_abi.encode(
            ["uint256"], [contract_data]
        )
        trxs = []
        for i in range(4):
            trxs.append(
                ScheduledTransaction(
                    neon_user.neon_address,
                    None,
                    nonce,
                    index=i,
                    target=basic_contract.eth_address,
                    value=0,
                    call_data=data,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(trxs[0], 3, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 3, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 3)
        tree_account = evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, SOL_MINT_ID
        )

        additional_accounts = [basic_contract.solana_address, neon_user.get_balance_account(SOL_CHAIN_ID)]
        for trx in trxs:
            evm_loader.execute_scheduled_trx_from_instruction(
                trx, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
            )
            evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)
        tree_account_data = neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce)
        assert tree_account_data.all_transactions_successful()
        evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_account)
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).transactions == []

    def test_deploy_and_call_contract(
        self, evm_loader, neon_user, neon_api_client, treasury_pool, operator_keypair, holder_acc, basic_contract
    ):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)
        contract_code = (
            get_contract_bin("common/Common", contract_name="CommonCaller", version="0.8.12")
            + eth_abi.encode(["address"], [basic_contract.eth_address.hex()]).hex()
        )
        caller_contract: Contract = create_contract_address(neon_user.neon_address, evm_loader, SOL_CHAIN_ID)

        emulate_deploy = neon_api_client.emulate(
            neon_user.neon_address.hex(), contract=None, data=contract_code, chain_id=SOL_CHAIN_ID
        )
        additional_accounts_deploy = [Pubkey.from_string(item["pubkey"]) for item in emulate_deploy["solana_accounts"]]

        data_call = abi.function_signature_to_4byte_selector("getNumber()")
        tx0 = ScheduledTransaction(
            neon_user.neon_address, None, nonce, index=0, call_data=bytes.fromhex(contract_code),
            target=None, gas_limit=193807600
        )
        tx1 = ScheduledTransaction(
            neon_user.neon_address, None, nonce, index=1, target=caller_contract.eth_address, call_data=data_call
        )

        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(tx0, 1, 0)
        tree_acc_data.add_trx(tx1, 0xFFFF, 1)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, SOL_MINT_ID
        )
        additional_accounts_call = [
            caller_contract.solana_address,
            basic_contract.solana_address,
            neon_user.get_balance_account(SOL_CHAIN_ID),
        ]
        evm_loader.write_transaction_to_holder_account(tx0.encode(), holder_acc, operator_keypair)
        evm_loader.execute_scheduled_trx_from_account(
            0, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts_deploy,
            compute_unit_price=15
        )

        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)

        evm_loader.execute_scheduled_trx_from_instruction(
            tx1, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts_call
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)
        tree_account_data = neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce)

        assert tree_account_data.all_transactions_successful()
        evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_account)
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).transactions == []

    def test_call_precompiled_by_scheduled_trx(
        self, evm_loader, neon_user, neon_api_client, treasury_pool, operator_keypair, holder_acc, spl_token_caller
    ):
        nonce = evm_loader.get_neon_nonce(neon_user.neon_address, SOL_CHAIN_ID)

        data = abi.function_signature_to_4byte_selector("initializeMint(uint8)") + eth_abi.encode(["uint8"], [9])
        emulate_result = neon_api_client.emulate(
            neon_user.neon_address.hex(), contract=spl_token_caller.eth_address.hex(), data=data, chain_id=SOL_CHAIN_ID
        )

        additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]

        tx0 = ScheduledTransaction(
            neon_user.neon_address, None, nonce, target=spl_token_caller.eth_address, index=0, value=0, call_data=data
        )

        tree_acc_data = CreateTreeAccMultipleData(nonce=nonce)
        tree_acc_data.add_trx(tx0, 0xFFFF, 0)

        tree_account = evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, SOL_MINT_ID
        )
        evm_loader.execute_scheduled_trx_from_instruction(
            tx0, operator_keypair, holder_acc, tree_account, treasury_pool, additional_accounts
        )
        evm_loader.finish_scheduled_trx(operator_keypair, tree_account, holder_acc)
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).all_transactions_successful()
        evm_loader.destroy_tree_account(operator_keypair, neon_user, treasury_pool, tree_account)
        assert neon_api_client.get_transaction_tree(neon_user.neon_address.hex(), nonce).transactions == []
