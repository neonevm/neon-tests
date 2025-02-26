import allure
import eth_abi
import pytest
from eth_utils import abi
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction
from solders.pubkey import Pubkey
from spl.token.instructions import get_associated_token_address, create_associated_token_account

from utils.consts import wSOL
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTransaction, CreateTreeAccMultipleData, ScheduledTrxEstimateRequest


@allure.feature("Solana native")
@allure.story("Test sending scheduled transaction for new ERC20ForSpl")
class TestScheduledTrxERC20new:

    def test_scheduled_trx_pda_balance(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)

        my_pda = Pubkey(erc20_spl_mintable_new.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())

        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        erc20_spl_mintable_new.pop_up_balance(evm_loader, recipient=neon_user, pda_amount=1000, ata_amount=1000)

        balance_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        assert (
            int(evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount) == balance_pda == 1000
        )

        data = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, 1000]
        )
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, erc20_spl_mintable_new.address, data)
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj])

        tx = ScheduledTransaction.from_estimate_result(0, trx_estimate_obj, estimate_result)

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)

        balance_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(neon_user.checksum_address).call()

        assert erc20_spl_mintable_new.get_balance(recipient.checksum_address) == 1000
        assert erc20_spl_mintable_new.get_balance(neon_user.checksum_address) == balance_ata == 1000

        assert int(evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount) == 0
        assert int(evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount) == 1000

    def test_scheduled_trx_no_pda_balance_uses_ata(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)

        my_pda = Pubkey(erc20_spl_mintable_new.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        erc20_spl_mintable_new.pop_up_balance(evm_loader, recipient=neon_user, pda_amount=1000, ata_amount=1000)

        assert int(evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount) == 1000

        data = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, 2000]
        )

        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        tx0 = ScheduledTransaction(
            nonce=nonce,
            index=0,
            target=erc20_spl_mintable_new.address,
            call_data=data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            payer=neon_user.checksum_address,
            sender=None,
        )

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx0.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)

        assert erc20_spl_mintable_new.get_balance(recipient.checksum_address) == 2000
        assert erc20_spl_mintable_new.get_balance(neon_user.checksum_address) == 0

        assert int(evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount) == 0
        assert int(evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount) == 0

    def test_scheduled_trx_both_pda_and_ata_used(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)
        amount_to_transfer = 1_000

        my_pda = Pubkey(erc20_spl_mintable_new.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        erc20_spl_mintable_new.pop_up_balance(
            evm_loader, recipient=neon_user, pda_amount=amount_to_transfer, ata_amount=amount_to_transfer
        )

        for account in (my_pda, my_ata):
            assert int(evm_loader.get_token_account_balance(account, commitment=Confirmed).value.amount) == 1000

        data = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, 2000]
        )

        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        tx0 = ScheduledTransaction(
            nonce=nonce,
            index=0,
            target=erc20_spl_mintable_new.address,
            call_data=data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            payer=neon_user.checksum_address,
            sender=None,
        )

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx0.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)

        balance_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        balance_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(neon_user.checksum_address).call()

        assert erc20_spl_mintable_new.get_balance(recipient.checksum_address) == 2000
        assert balance_pda == balance_ata == 0

    def test_scheduled_trx_transfer_solana_ata_balance_not_used(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):

        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())

        erc20_spl_mintable_new.pop_up_balance(evm_loader, recipient=neon_user, pda_amount=5, ata_amount=2000)
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        data = abi.function_signature_to_4byte_selector("transferSolana(address,uint256)") + eth_abi.encode(
            ["bytes", "uint256"], [bytes(my_ata), 10]
        )

        gas_limit = 3000000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2500000000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        tx0 = ScheduledTransaction(
            nonce=nonce,
            index=0,
            target=erc20_spl_mintable_new.address,
            call_data=data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            payer=neon_user.checksum_address,
            sender=None,
        )

        evm_loader.create_tree_account(
            neon_user, treasury_pool, tx0.encode(), wSOL["address_spl"], chain_id=evm_loader.sol_chain_id
        )
        resp = web3_client_sol.wait_for_transaction_receipt(tx0.hash(), timeout=180)

        assert resp["status"] == 0, resp

    @pytest.mark.xfail(reason="NDEV-3575")
    def test_multiple_transactions_with_transfer_from_solana(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):

        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)

        trx = Transaction()
        trx.add(
            create_associated_token_account(
                neon_user.solana_account.pubkey(), neon_user.solana_account.pubkey(), token_mint
            )
        )
        evm_loader.send_tx_and_check_status_ok(trx, neon_user.solana_account)
        amount = 1000

        erc20_spl_mintable_new.approve(erc20_spl_mintable_new.account, neon_user.checksum_address, amount)

        call_data = abi.function_signature_to_4byte_selector(
            "transferSolanaFrom(address,bytes,uint64)"
        ) + eth_abi.encode(
            ["address", "bytes", "uint64"],
            [erc20_spl_mintable_new.account.address, bytes(my_ata), amount],
        )

        gas_limit = 3_000_000
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2_500_000_000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        tx = ScheduledTransaction(
            nonce=nonce,
            index=0,
            target=erc20_spl_mintable_new.address,
            call_data=call_data,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            gas_limit=gas_limit,
            payer=neon_user.checksum_address,
            sender=None,
        )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        tree_acc_data.add_trx(tx, 0xFFFF, 0)

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_scheduled_transaction(tx)

        resp = web3_client_sol.wait_for_transaction_receipt(tx.hash(), timeout=180)
        assert resp["status"] == 1, resp

    def test_multiple_transactions_with_tree_actions_dependent_trx(
        self,
        web3_client_sol,
        neon_user,
        erc20_spl_mintable_new,
        evm_loader,
        treasury_pool,
        sol_client,
    ):
        # ┌───────┐  ┌──────┐
        # │ t0 ✓  ├─>┤ t2 ✓ │
        # │ s=0   │  │ s=1  │
        # └───────┘  └──────┘
        # ┌───────┐  ┌──────┐
        # │ t1 ✓  ├─>┤ t3 ✓ │
        # │ s=0   │  │ s=1  │
        # └───────┘  └──────┘
        recipient = NeonUser(evm_loader.loader_id)  # Recipient #1

        erc20_spl_mintable_new.approve(erc20_spl_mintable_new.account, neon_user.checksum_address, 800)

        top_up_in_trx = 400
        amount_to_recipient = 400

        data_0 = data_1 = abi.function_signature_to_4byte_selector(
            "transferFrom(address,address,uint256)"
        ) + eth_abi.encode(
            ["address", "address", "uint256"],
            [erc20_spl_mintable_new.account.address, neon_user.checksum_address, top_up_in_trx],
        )

        data_2 = data_3 = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, amount_to_recipient]
        )

        call_data: list = [data_0, data_1, data_2, data_3]

        # TODO Use estimate result method to count transaction fees. Waiting for developers to fix it.

        gas_limit = 3_000_000
        trx_count = 4
        base_fee_per_gas = web3_client_sol.base_fee_per_gas()
        max_priority_fee_per_gas = 2_500_000_000
        max_fee_per_gas = base_fee_per_gas * 2 + max_priority_fee_per_gas
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        trxs = []
        for i in range(trx_count):
            trxs.append(
                ScheduledTransaction(
                    nonce=nonce,
                    index=i,
                    target=erc20_spl_mintable_new.address,
                    call_data=call_data[i],
                    max_fee_per_gas=max_fee_per_gas,
                    max_priority_fee_per_gas=max_priority_fee_per_gas,
                    gas_limit=gas_limit,
                    payer=neon_user.checksum_address,
                    sender=None,
                )
            )

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
        )

        tree_acc_data.add_trx(trxs[0], 2, 0)
        tree_acc_data.add_trx(trxs[1], 3, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 1)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 1)

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)

        for trx in trxs:
            assert (
                web3_client_sol.wait_for_transaction_receipt(trx.hash(), timeout=180)["status"] == 1
            ), f"transaction_{trx.index} failed"

        balance_user_1 = erc20_spl_mintable_new.get_balance(neon_user.checksum_address)
        balance_user_2 = erc20_spl_mintable_new.get_balance(recipient.checksum_address)

        balance_user_1_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        balance_user_1_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(neon_user.checksum_address).call()
        balance_user_2_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(recipient.checksum_address).call()
        balance_user_2_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(recipient.checksum_address).call()

        assert balance_user_1 == balance_user_1_ata == balance_user_1_pda == 0
        assert balance_user_2_ata == 0
        assert balance_user_2 == balance_user_2_pda == 800

    def test_multiple_transactions_with_tree_actions_independent(
        self, web3_client_sol, neon_user, erc20_spl_mintable_new, evm_loader, treasury_pool
    ):

        recipient = NeonUser(evm_loader.loader_id)

        amount_to_transfer = 1_000

        my_pda = Pubkey(erc20_spl_mintable_new.contract.functions.solanaAccount(neon_user.checksum_address).call())
        token_mint = Pubkey(erc20_spl_mintable_new.contract.functions.tokenMint().call())
        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), token_mint)
        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)

        erc20_spl_mintable_new.pop_up_balance(
            evm_loader, recipient=neon_user, pda_amount=amount_to_transfer, ata_amount=amount_to_transfer
        )

        assert (
            int(evm_loader.get_token_account_balance(my_ata, commitment=Confirmed).value.amount) == amount_to_transfer
        )
        assert (
            int(evm_loader.get_token_account_balance(my_pda, commitment=Confirmed).value.amount) == amount_to_transfer
        )

        transfer_amount = 200
        burn_amount = 100
        approve_amount = 1000
        trx_count = 4

        data_0 = abi.function_signature_to_4byte_selector("approve(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [neon_user.checksum_address, approve_amount]
        )
        data_1 = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, transfer_amount]
        )
        data_2 = abi.function_signature_to_4byte_selector("burn(uint256)") + eth_abi.encode(["uint256"], [burn_amount])
        data_3 = abi.function_signature_to_4byte_selector("transfer(address,uint256)") + eth_abi.encode(
            ["address", "uint256"], [recipient.checksum_address, transfer_amount]
        )
        call_data: list = [data_0, data_1, data_2, data_3]

        # TODO Use estimate result method to count transaction fees. Waiting for developers to fix it.
        trx_estimate_obj_list: list[ScheduledTrxEstimateRequest] = []
        for i in range(trx_count):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, erc20_spl_mintable_new.address, call_data[i])
            )
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)

        trxs = []
        for i in range(trx_count):
            trxs.append(ScheduledTransaction.from_estimate_result(i, trx_estimate_obj_list[i], estimate_result))

        tree_acc_data = CreateTreeAccMultipleData(
            nonce=nonce,
            max_fee_per_gas=estimate_result["maxFeePerGas"],
            max_priority_fee_per_gas=estimate_result["maxPriorityFeePerGas"],
        )
        tree_acc_data.add_trx(trxs[0], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[1], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[2], 0xFFFF, 0)
        tree_acc_data.add_trx(trxs[3], 0xFFFF, 0)

        evm_loader.create_tree_account_multiple(
            neon_user, treasury_pool, tree_acc_data.data, wSOL["address_spl"], chain_id=web3_client_sol.chain_id
        )
        web3_client_sol.send_all_scheduled_transactions(trxs)
        for trx in trxs:
            assert (
                web3_client_sol.wait_for_transaction_receipt(trx.hash(), timeout=180)["status"] == 1
            ), f"transaction_{trx.index} failed"

        balance_pda = erc20_spl_mintable_new.contract.functions.balanceOfPDA(neon_user.checksum_address).call()
        balance_ata = erc20_spl_mintable_new.contract.functions.balanceOfATA(neon_user.checksum_address).call()

        assert erc20_spl_mintable_new.get_balance(recipient.checksum_address) == transfer_amount * 2
        assert balance_pda == amount_to_transfer - transfer_amount * 2 - burn_amount
        assert balance_ata == amount_to_transfer
