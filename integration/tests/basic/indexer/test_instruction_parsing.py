import pytest
from eth_utils import keccak
from eth_abi import abi
from solana.transaction import AccountMeta, Instruction

import allure
from solders.pubkey import Pubkey

from integration.tests.basic.helpers.rpc_checks import (
    assert_instructions,
    assert_solana_trxs_in_neon_receipt,
    count_instructions,
)
from utils.accounts import EthAccounts
from utils.consts import COUNTER_ID, ZERO_ADDRESS
from utils.helpers import gen_hash_of_block, generate_text, serialize_instruction, get_selectors
from utils.models.result import NeonGetTransactionResult
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify events")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
@pytest.mark.neon_only
class TestInstruction:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def test_tx_exec_from_data(self, json_rpc_client):
        sender_account, receiver_account = self.accounts[0], self.accounts[1]
        tx = self.web3_client.make_raw_tx(sender_account, receiver_account, amount=1000000, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert_instructions(validated_response)
        assert "TxExecFromData" in count_instructions(validated_response).keys()
        assert_solana_trxs_in_neon_receipt(json_rpc_client, resp["transactionHash"], validated_response)

    def test_cancel_with_hash(self, json_rpc_client, expected_error_checker):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = expected_error_checker.functions.method1().build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert_instructions(validated_response)
        assert "CancelWithHash" in count_instructions(validated_response).keys()
        assert_solana_trxs_in_neon_receipt(json_rpc_client, resp["transactionHash"], validated_response)

    def test_tx_exec_from_data_solana_call(self, call_solana_caller, counter_resource_address: bytes, json_rpc_client):
        sender = self.accounts[0]
        lamports = 0

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.executeWithGetReturnData(lamports, serialized).build_transaction(
            tx
        )
        resp = self.web3_client.send_transaction(sender, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert_instructions(validated_response)
        assert "TxExecFromDataSolanaCall" in count_instructions(validated_response).keys()
        assert_solana_trxs_in_neon_receipt(json_rpc_client, resp["transactionHash"], validated_response)

    @pytest.mark.parametrize(
        "remove_chain_id, expected_instruction",
        [(True, "TxStepFromAccountNoChainId"), (False, "TxStepFromData")],
    )
    def test_tx_iterative_with_and_without_chain_id(
        self, counter_contract, json_rpc_client, remove_chain_id, expected_instruction
    ):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender_account, estimate_gas=True)
        if remove_chain_id:
            tx["chainId"] = None
        instruction_tx = counter_contract.functions.moreInstructionWithLogs(0, 1000).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert_instructions(validated_response)
        assert expected_instruction in count_instructions(validated_response).keys()
        assert_solana_trxs_in_neon_receipt(json_rpc_client, resp["transactionHash"], validated_response)

    def test_holder_write_tx_exec_from_account(self, multiple_actions_erc721, json_rpc_client):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc721

        tx = self.web3_client.make_raw_tx(sender_account)
        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.mint(seed, uri).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)
        token_id = contract.functions.lastTokenId().call()

        tx = self.web3_client.make_raw_tx(sender_account)
        seed = self.web3_client.text_to_bytes32(gen_hash_of_block(8))
        uri = generate_text(min_len=10, max_len=200)
        instruction_tx = contract.functions.transferMint(acc.address, seed, token_id, uri).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender_account, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert_instructions(validated_response)
        assert "HolderWrite" in count_instructions(validated_response).keys()
        assert "TxExecFromAccount" in count_instructions(validated_response).keys()
        assert_solana_trxs_in_neon_receipt(json_rpc_client, resp["transactionHash"], validated_response)

    @pytest.mark.skip(reason="NDEV-3616")
    def test_step_from_account(self, json_rpc_client, diamond):
        sender_account = self.accounts[0]

        new_facet, _ = self.web3_client.deploy_and_get_contract(
            "EIPs/EIP2535/facets/Test1Facet",
            "0.8.10",
            sender_account,
            contract_name="Test1Facet",
        )
        facet_cuts = [(new_facet.address, 0, get_selectors(new_facet.abi))]
        calldata = keccak(text="diamondCut((address,uint8,bytes4[])[],address,bytes)")[:4] + abi.encode(
            ["(address,uint8,bytes4[])[]", "address", "bytes"],
            [facet_cuts, ZERO_ADDRESS, b"0x"],
        )

        tx = self.web3_client.make_raw_tx(sender_account, diamond.address, 0, data=calldata, estimate_gas=True)
        resp = self.web3_client.send_transaction(sender_account, tx)
        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert_instructions(validated_response)
        assert "TxStepFromAccount" in count_instructions(validated_response).keys()
        assert_solana_trxs_in_neon_receipt(json_rpc_client, resp["transactionHash"], validated_response)

    def test_tx_exec_from_account_solana_call(
        self, call_solana_caller, counter_resource_address: bytes, json_rpc_client
    ):
        sender = self.accounts[0]
        call_params = []

        for _ in range(10):
            instruction = Instruction(
                program_id=COUNTER_ID,
                accounts=[
                    AccountMeta(Pubkey(counter_resource_address), is_signer=False, is_writable=True),
                ],
                data=bytes([0x1]),
            )
            serialized = serialize_instruction(COUNTER_ID, instruction)
            call_params.append((0, serialized))

        tx = self.web3_client.make_raw_tx(sender.address)
        instruction_tx = call_solana_caller.functions.batchExecute(call_params).build_transaction(tx)
        resp = self.web3_client.send_transaction(sender, instruction_tx)

        response = json_rpc_client.get_neon_trx_receipt(resp["transactionHash"])
        validated_response = NeonGetTransactionResult(**response)

        assert_instructions(validated_response)
        assert "TxExecFromAccountSolanaCall" in count_instructions(validated_response).keys()
        assert_solana_trxs_in_neon_receipt(json_rpc_client, resp["transactionHash"], validated_response)
