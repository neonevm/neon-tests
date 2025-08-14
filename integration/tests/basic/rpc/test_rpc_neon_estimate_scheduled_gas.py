import allure
import base58
import pytest
from solana.transaction import Transaction
from solders.pubkey import Pubkey

from eth_utils import abi
import solders.system_program as sp
from solders.token.associated import get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import (
    ApproveParams,
    create_associated_token_account,
    approve,
    sync_native,
    SyncNativeParams,
)

from integration.tests.basic.helpers.errors import Error32602, Error32000, Error3, Error32603

from integration.tests.basic.helpers.rpc_checks import assert_fields_are_hex, is_hex
from utils.consts import LAMPORT_PER_SOL
from utils.helpers import decode_function_signature
from utils.models.result import EstimateScheduledGas
from utils.neon_user import NeonUser
from utils.scheduled_trx import ScheduledTrxEstimateRequest


@allure.feature("JSON-RPC validation")
@allure.story("Verify JSON-RPC neon_estimateScheduledGas work")
@pytest.mark.neon_only
class TestNeonRPCEstimateScheduledGas:

    def test_estimate_one_transaction(self, web3_client_sol, neon_user, common_contract, evm_loader):

        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), [trx_estimate_obj], check_result=False
        )

        EstimateScheduledGas(**resp)
        chain_id = web3_client_sol.chain_id
        result = resp["result"]
        assert (
            len(result["gasList"]) == 1
        ), f'Amount of transactions must be 1, but actual amount = {len(result["gasList"])}'

        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        assert result["nonce"] == hex(nonce)
        assert result["maxFeePerGas"] > result["maxPriorityFeePerGas"], (
            f"maxFeePerGas must be greater than maxPriorityFeePerGas, "
            f'but maxFeePerGas = {result["maxFeePerGas"]} and maxPriorityFeePerGas = {result["maxPriorityFeePerGas"]}'
        )

        assert result["chainId"] == hex(chain_id), f'ChainID must be {chain_id}, but actual = {result["chainId"]}'
        assert (
            len(result["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(result["accountList"])}'

        balance_account = str(neon_user.get_balance_account(chain_id))
        treasury_index = int(result["treasuryIndex"], 16)
        treasury_address = str(evm_loader.create_treasury_pool_address(treasury_index))

        tree_account = evm_loader.create_tree_account_address(
            neon_user.neon_address, nonce.to_bytes(8, "little"), chain_id
        )
        authority_pool = Pubkey.find_program_address([b"Deposit"], evm_loader.loader_id)[0]

        assert result["accountList"][0] == str(neon_user.solana_account.pubkey())
        assert result["accountList"][1] == balance_account
        assert result["accountList"][2] == treasury_address
        assert result["accountList"][3] == str(tree_account)
        assert result["accountList"][4] == str(authority_pool)
        assert result["accountList"][5] == str(sp.ID)

    def test_send_multiple_transactions(self, web3_client_sol, neon_user, common_contract, evm_loader):
        transaction_rate = 4
        chain_id = web3_client_sol.chain_id

        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj_list = []
        for i in range(transaction_rate):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
            )

        resp = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)
        assert (
            len(resp["gasList"]) == transaction_rate
        ), f"Amount of transactions must be 1, but actual amount = {transaction_rate}"

        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        assert resp["nonce"] == hex(nonce)
        assert resp["maxFeePerGas"] > resp["maxPriorityFeePerGas"], (
            f"maxFeePerGas must be greater than maxPriorityFeePerGas, "
            f'but maxFeePerGas = {resp["maxFeePerGas"]} and maxPriorityFeePerGas = {resp["maxPriorityFeePerGas"]}'
        )
        assert_fields_are_hex(resp, ["chainId", "maxFeePerGas", "maxPriorityFeePerGas", "nonce", "treasuryIndex"])
        assert resp["chainId"] == hex(chain_id), f'ChainID must be {chain_id}, but actual = {resp["chainId"]}'
        assert (
            len(resp["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(resp["accountList"])}'

        balance_account = str(neon_user.get_balance_account(chain_id))
        treasury_index = int(resp["treasuryIndex"], 16)
        treasury_address = str(evm_loader.create_treasury_pool_address(treasury_index))

        tree_account = evm_loader.create_tree_account_address(
            neon_user.neon_address, nonce.to_bytes(8, "little"), chain_id
        )
        authority_pool = Pubkey.find_program_address([b"Deposit"], evm_loader.loader_id)[0]

        assert resp["accountList"][0] == str(neon_user.solana_account.pubkey())
        assert resp["accountList"][1] == balance_account
        assert resp["accountList"][2] == treasury_address
        assert resp["accountList"][3] == str(tree_account)
        assert resp["accountList"][4] == str(authority_pool)
        assert resp["accountList"][5] == str(sp.ID)

    def test_one_of_multiply_transactions_failed(
        self,
        web3_client_sol,
        neon_user,
        revert_contract_caller,
        event_caller_contract,
        common_contract,
        evm_loader,
    ):
        transaction_rate = 3
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj_list = []
        for i in range(transaction_rate):
            trx_estimate_obj_list.append(
                ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
            )

        data_fail_tx = abi.function_signature_to_4byte_selector("doAssert()")
        trx_estimate_obj_list.append(
            ScheduledTrxEstimateRequest(neon_user.checksum_address, revert_contract_caller.address, data_fail_tx.hex())
        )

        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list, check_result=False
        )

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert "message" in resp["error"], "message field not in response"
        assert resp["error"]["code"] == Error3.CODE, f"code must be {Error32603.CODE}"
        assert (
            Error3.EXECUTION_REVERTED in resp["error"]["message"]
        ), f"message must be {Error3.EXECUTION_REVERTED}, got - {resp['error']['message']}"

    def test_no_transactions_in_request(self, web3_client_sol, neon_user, common_contract, evm_loader):
        resp = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), [], check_result=False)

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert "message" in resp["error"], "message field not in response"
        assert Error32602.CODE == resp["error"]["code"]
        assert Error32602.INVALID_TRANSACTIONID == resp["error"]["message"]

    def test_send_value_greater_than_balance(self, web3_client_sol, neon_user, evm_loader, event_caller_sol_chain):
        evm_loader.deposit_wrapped_sol_from_solana_to_neon(
            neon_user.solana_account,
            "0x" + neon_user.neon_address.hex(),
            int(1 * LAMPORT_PER_SOL),
        )

        balance = web3_client_sol.get_balance(neon_user.checksum_address)
        call_data = decode_function_signature("indexedArgs()")
        value = balance + 10

        trx_estimate_obj = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, event_caller_sol_chain.address, call_data, value=value
        )

        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), [trx_estimate_obj], check_result=False
        )

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert "message" in resp["error"], "message field not in response"
        assert resp["error"]["code"] == Error3.CODE, f"code must be {Error3.CODE}"
        assert (
            Error3.EXECUTION_REVERTED in resp["error"]["message"]
        ), f"message must be {Error3.EXECUTION_REVERTED}, got - {resp['error']['message']}"

    def test_sender_has_no_sols(self, web3_client_sol, common_contract, evm_loader, neon_user_no_sols):
        chain_id = web3_client_sol.chain_id
        data = decode_function_signature("setNumber(uint256)", [18])

        trx_estimate_obj = ScheduledTrxEstimateRequest(
            neon_user_no_sols.checksum_address, common_contract.address, data
        )
        resp = web3_client_sol.estimate_scheduled(neon_user_no_sols.solana_account.pubkey(), [trx_estimate_obj])

        assert (
            len(resp["gasList"]) == 1
        ), f'Amount of transactions must be 1, but actual amount = {len(resp["gasList"])}'

        nonce = web3_client_sol.get_nonce(neon_user_no_sols.checksum_address)
        assert resp["nonce"] == hex(nonce)
        assert resp["maxFeePerGas"] > resp["maxPriorityFeePerGas"], (
            f"maxFeePerGas must be greater than maxPriorityFeePerGas, "
            f'but maxFeePerGas = {resp["maxFeePerGas"]} and maxPriorityFeePerGas = {resp["maxPriorityFeePerGas"]}'
        )

        assert_fields_are_hex(resp, ["chainId", "maxFeePerGas", "maxPriorityFeePerGas", "nonce", "treasuryIndex"])
        assert resp["chainId"] == hex(chain_id), f'ChainID must be {chain_id}, but actual = {resp["chainId"]}'
        assert (
            len(resp["accountList"]) == 6
        ), f'Amount of accounts must be 6, but actual amount = {len(resp["accountList"])}'

    def test_no_function_in_called_contract(self, web3_client_sol, neon_user, revert_contract_caller, evm_loader):
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, revert_contract_caller.address, data)
        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), [trx_estimate_obj], check_result=False
        )

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert "message" in resp["error"], "message field not in response"
        assert Error3.CODE == resp["error"]["code"], f"error code must be {Error3.CODE} "
        assert (
            Error3.EXECUTION_REVERTED == resp["error"]["message"]
        ), f"error message must be {Error3.EXECUTION_REVERTED}"

    def test_wrong_chain_id(self, web3_client, web3_client_sol, neon_user, common_contract):
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)
        resp = web3_client.estimate_scheduled(neon_user.solana_account.pubkey(), [trx_estimate_obj], check_result=False)

        assert "error" in resp, "error field not in response"
        assert "code" in resp["error"]
        assert "message" in resp["error"], "message field not in response"

        assert Error32000.CODE == resp["error"]["code"], f"error code must be {Error32000.CODE}"
        assert (
            Error32000.WRONG_CHAIN_ID == resp["error"]["message"]
        ), f"error message must be {Error32000.WRONG_CHAIN_ID}"

    @pytest.mark.parametrize(
        "field, invalid_value,error_code,error_msg",
        [
            ("fromAddress", "invalid_from_address", Error32602.CODE, Error32602.INVALID_PARAMETERS),
            ("toAddress", "invalid_to_address", Error32602.CODE, Error32602.INVALID_PARAMETERS),
            ("data", "random data", Error32602.CODE, Error32602.INVALID_PARAMETERS),
            ("value", -100, Error32602.CODE, Error32602.INVALID_PARAMETERS),
        ],
    )
    def test_wrong_format_field(
        self,
        json_rpc_client,
        neon_user,
        common_contract,
        field,
        invalid_value,
        error_code,
        error_msg,
    ):

        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate_obj = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data)

        tx = {
            "fromAddress": trx_estimate_obj.from_address,
            "toAddress": trx_estimate_obj.to_address,
            "data": trx_estimate_obj.data,
            "value": trx_estimate_obj.value,
            field: invalid_value,
        }
        params = {"scheduledSolanaPayer": str(neon_user.solana_account.pubkey()), "transactions": [tx]}

        resp = json_rpc_client.send_rpc(method="neon_estimateScheduledGas", params=params)
        assert "error" in resp, "error field not in response"
        assert resp["error"]["code"] == error_code, f"error code must be {error_code} "
        assert resp["error"]["message"] == error_msg, f"error message must be {error_msg}"

    def test_one_transaction_no_child(self, web3_client_sol, neon_user, common_contract):
        data = decode_function_signature("setNumber(uint256)", [18])
        trx_estimate = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, common_contract.address, data, child_transaction="0xFFFF"
        )
        trx_estimate_obj_list = [trx_estimate]
        estimate_result = web3_client_sol.estimate_scheduled(neon_user.solana_account.pubkey(), trx_estimate_obj_list)

        assert len(estimate_result["gasList"]) == 1
        assert is_hex(estimate_result["gasList"][0])

    def test_wrong_transactions_order_in_request(
        self,
        web3_client_sol,
        neon_user,
        erc20_spl_mintable,
        evm_loader,
    ):
        # ┌───────┐  ┌──────┐  ┌───────┐
        # │ t2 ✓  ├─>┤ t0 ✓ │─>│ t1 ✓  ├
        # │ s=0   │  │ s=1  │  │ s=2   │
        # └───────┘  └──────┘  └───────┘
        recipient = NeonUser(evm_loader.loader_id)
        erc20_spl_mintable.approve(erc20_spl_mintable.owner, neon_user.checksum_address, 800)
        top_up_in_trx = 400
        amount_to_recipient = 400

        data_0 = data_2 = decode_function_signature(
            "transferFrom(address,address,uint256)",
            [erc20_spl_mintable.owner.address, neon_user.checksum_address, top_up_in_trx],
        )
        data_1 = decode_function_signature(
            "transfer(address,uint256)", [recipient.checksum_address, amount_to_recipient]
        )

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_0, child_transaction=hex(1)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_1, child_transaction=hex(2)
        )
        trx_estimate_2 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, erc20_spl_mintable.address, data_2, child_transaction="0xFFFF"
        )

        trx_estimate_obj_list = [trx_estimate_2, trx_estimate_0, trx_estimate_1]

        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list, check_result=False
        )

        assert estimate_result["error"]["code"] == Error32603.CODE
        assert estimate_result["error"]["message"] == Error32603.INTERNAL_ERROR
        assert estimate_result["error"]["data"]["errors"][0] == "childTransaction 1 in 1 should be more than 1"

    def test_non_existent_child_idx(self, web3_client_sol, neon_user, evm_loader, common_contract):
        # ┌──────┐  ┌───────┐
        # ┤ t0 ✓ │─>│ t1 ✓  ├
        # │ s=1  │  │ s=2   │
        # └──────┘  └───────┘

        data_0 = decode_function_signature("setNumber(uint256)", [1998])
        data_1 = decode_function_signature("setNumber(uint256)", [2007])

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, common_contract.address, data_0, child_transaction=hex(1)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, common_contract.address, data_1, child_transaction=hex(2)
        )

        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1]

        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list, check_result=False
        )

        assert estimate_result["error"]["code"] == Error32603.CODE
        assert estimate_result["error"]["message"] == Error32603.INTERNAL_ERROR
        assert estimate_result["error"]["data"]["errors"][0] == "childTransaction 2 in 1 should be less than 2"

    @pytest.mark.parametrize("value", (1.0, "1.0", "first", "", 0))
    def test_invalid_type_child_transaction_field(self, web3_client_sol, neon_user, evm_loader, common_contract, value):
        # ┌──────┐  ┌───────┐
        # ┤ t0 ✓ │─>│ t1 ✓  ├
        # │ s=1  │  │ s=2   │
        # └──────┘  └───────┘
        data_0 = decode_function_signature("setNumber(uint256)", [1998])
        data_1 = decode_function_signature("setNumber(uint256)", [2007])

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, common_contract.address, data_0, child_transaction=value
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, common_contract.address, data_1, child_transaction="0xFFFF"
        )

        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1]

        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list, check_result=False
        )

        assert estimate_result["error"]["code"] == Error32602.CODE
        assert estimate_result["error"]["message"] == Error32602.INVALID_PARAMETERS
        assert "Value error" in estimate_result["error"]["data"]["errors"][0]

    def test_estimate_child_transaction_reverted(
        self, web3_client_sol, neon_user, evm_loader, revert_contract, common_contract
    ):
        # ┌──────┐  ┌───────────┐
        # ┤ t0 ✓ │─>│ t1, revert├
        # │ s=1  │  │ s=0,      │
        # └──────┘  └───────────┘
        data_0 = decode_function_signature("setNumber(uint256)", [1998])

        data_1 = decode_function_signature("doAssert()")

        trx_estimate_0 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, common_contract.address, data_0, child_transaction=hex(1)
        )
        trx_estimate_1 = ScheduledTrxEstimateRequest(
            neon_user.checksum_address, revert_contract.address, data_1, child_transaction="0xFFFF"
        )

        trx_estimate_obj_list = [trx_estimate_0, trx_estimate_1]

        estimate_result = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), trx_estimate_obj_list, check_result=False
        )

        assert estimate_result["error"]["code"] == Error3.CODE
        assert Error3.EXECUTION_REVERTED in estimate_result["error"]["message"]

    def test_estimate_with_preparatory_solana_transactions(
        self, web3_client_sol, neon_user, erc20_spl_mintable, evm_loader, common_contract
    ):
        recipient = NeonUser(evm_loader.loader_id)
        ata_amount = 1_000
        erc20_spl_mintable.approve(erc20_spl_mintable.owner, neon_user.checksum_address, ata_amount)

        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), erc20_spl_mintable.token_mint_pubkey)
        solana_contract_account = evm_loader.ether2program(erc20_spl_mintable.contract.address)

        trx = Transaction()
        trx.add(
            create_associated_token_account(
                neon_user.solana_account.pubkey(),
                neon_user.solana_account.pubkey(),
                erc20_spl_mintable.token_mint_pubkey,
            )
        )
        trx.add(
            approve(
                ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=my_ata,
                    delegate=solana_contract_account,
                    owner=neon_user.solana_account.pubkey(),
                    amount=ata_amount,
                )
            )
        )

        data1 = decode_function_signature(
            "transferSolanaFrom(address,bytes32,uint64)",
            [erc20_spl_mintable.owner.address, bytes(my_ata), ata_amount],
        )
        data2 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, ata_amount])

        trx_estimate_obj1 = ScheduledTrxEstimateRequest(neon_user.checksum_address, erc20_spl_mintable.address, data1)
        trx_estimate_obj2 = ScheduledTrxEstimateRequest(neon_user.checksum_address, erc20_spl_mintable.address, data2)

        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(),
            [trx_estimate_obj1, trx_estimate_obj2],
            preparatory_solana_trxs=trx.instructions,
        )
        assert len(resp["gasList"]) == 2, "Amount of transactions must be 2"

        nonce = web3_client_sol.get_nonce(neon_user.checksum_address)
        assert resp["nonce"] == hex(nonce)
        assert_fields_are_hex(resp, ["chainId", "maxFeePerGas", "maxPriorityFeePerGas", "nonce", "treasuryIndex"])

    def test_estimate_transfer_trx_without_approval_in_preparatory_sol_trx_list(
        self, web3_client_sol, neon_user, erc20_spl_mintable, evm_loader, treasury_pool
    ):
        recipient = NeonUser(evm_loader.loader_id)
        ata_amount = 1_000
        erc20_spl_mintable.approve(erc20_spl_mintable.owner, neon_user.checksum_address, ata_amount)

        my_ata = get_associated_token_address(neon_user.solana_account.pubkey(), erc20_spl_mintable.token_mint_pubkey)

        data1 = decode_function_signature(
            "transferSolanaFrom(address,bytes32,uint64)",
            [erc20_spl_mintable.owner.address, bytes(my_ata), ata_amount],
        )
        data2 = decode_function_signature("transfer(address,uint256)", [recipient.checksum_address, ata_amount])

        trx_estimate_obj1 = ScheduledTrxEstimateRequest(neon_user.checksum_address, erc20_spl_mintable.address, data1)
        trx_estimate_obj2 = ScheduledTrxEstimateRequest(neon_user.checksum_address, erc20_spl_mintable.address, data2)

        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(), [trx_estimate_obj1, trx_estimate_obj2], check_result=False
        )
        assert "execution reverted" in resp["error"]["message"], "Error message is not correct"

    @pytest.mark.parametrize("case, value", [("wrong_data", "-"), ("wrong_accounts", []), ("wrong_instructions", [])])
    def test_wrong_params_value_estimate_with_preparatory_solana_transactions(
        self, neon_user, json_sol_rpc_client, case, value, common_contract
    ):
        trx = Transaction()
        trx.add(sync_native(SyncNativeParams(program_id=TOKEN_PROGRAM_ID, account=neon_user.solana_account.pubkey())))

        data1 = decode_function_signature("setTextAndReceiveValue(uint256)", [1998])

        trx_estimate_obj1 = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data1)

        solana_payer = neon_user.solana_account.pubkey()
        trx_list_estimate = [trx_estimate_obj1]
        preparatory_solana_trxs = trx.instructions
        transactions = []
        for trx in trx_list_estimate:
            transaction = {
                "fromAddress": trx.from_address,
                "toAddress": trx.to_address,
                "data": trx.data,
                "value": trx.value,
            }
            transactions.append(transaction)
        params = {"scheduledSolanaPayer": str(solana_payer), "transactions": transactions}

        instructions = []
        for trx in preparatory_solana_trxs:
            instruction = {"programId": str(trx.program_id), "data": base58.b58encode(trx.data).decode("utf-8")}
            accounts = []
            for account in trx.accounts:
                accounts.append(
                    {
                        "address": str(account.pubkey),
                        "isWritable": account.is_writable,
                        "isSigner": account.is_signer,
                    }
                )
            instruction["accounts"] = accounts
            instructions.append(instruction)
        params["preparatorySolanaTransactions"] = [{"instructions": instructions}]

        if case == "wrong_data":
            params["preparatorySolanaTransactions"][0]["instructions"][0]["data"] = value
        elif case == "wrong_accounts":
            params["preparatorySolanaTransactions"][0]["instructions"][0]["accounts"] = value
        elif case == "wrong_instructions":
            params["preparatorySolanaTransactions"] = [{"instructions": value}]

        resp = json_sol_rpc_client.send_rpc(method="neon_estimateScheduledGas", params=params)

        assert resp["error"]["code"] == Error32602.CODE
        assert resp["error"]["message"] == Error32602.INVALID_PARAMETERS
        assert "Value error" in resp["error"]["data"]["errors"][0]

    def test_estimate_with_preparatory_failed_solana_transaction(
        self, web3_client_sol, neon_user, evm_loader, common_contract
    ):
        trx = Transaction()
        trx.add(
            sync_native(
                SyncNativeParams(program_id=ASSOCIATED_TOKEN_PROGRAM_ID, account=neon_user.solana_account.pubkey())
            )
        )

        data1 = decode_function_signature("setTextAndReceiveValue(uint256)", [1998])

        trx_estimate_obj1 = ScheduledTrxEstimateRequest(neon_user.checksum_address, common_contract.address, data1)

        resp = web3_client_sol.estimate_scheduled(
            neon_user.solana_account.pubkey(),
            [
                trx_estimate_obj1,
            ],
            preparatory_solana_trxs=trx.instructions,
            check_result=False,
        )
        assert resp["error"]["code"] == 117
        assert "invalid instruction data" in resp["error"]["message"], "wrong error message"
