import random

import allure
import pytest
from solders.instruction import Instruction, AccountMeta
from solders.pubkey import Pubkey

from utils.accounts import EthAccounts
from utils.consts import COUNTER_ID
from utils.helpers import serialize_instruction
from utils.web3client import NeonChainWeb3Client


@allure.feature("Containers")
@allure.story("Send trxs by accounts in containers")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestContainerizedAccounts:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    def test_call_contract_in_container_by_acc_in_container(
        self, distributor_contract, evm_loader, treasury_pool, operator
    ):
        acc_in_container = self.accounts[1]
        balance_before = self.web3_client.get_balance(acc_in_container.address)

        sender = self.accounts[0]
        tx = self.web3_client.make_raw_tx(sender)
        instruction_tx = distributor_contract.functions.set_address(
            "alice", bytes.fromhex(acc_in_container.address[2:])
        ).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

        container_address = evm_loader.ether2program(distributor_contract.address[2:])
        evm_loader.assemble_container(
            operator=operator.operator_keypairs[0],
            treasury=treasury_pool,
            container_address=container_address,
            accounts=[evm_loader.ether2balance(acc_in_container.address[2:])],
        )
        amount = 300
        tx = self.web3_client.make_raw_tx(sender, amount=amount)
        instruction_tx = distributor_contract.functions.distribute_value().build_transaction(tx)

        receipt = self.web3_client.send_transaction(sender, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"
        balance_after = self.web3_client.get_balance(acc_in_container.address)
        assert balance_after == balance_before + amount, "Balance should be updated correctly"

        # sign trx by account added to container
        tx = self.web3_client.make_raw_tx(acc_in_container, amount=amount)
        instruction_tx = distributor_contract.functions.distribute_value().build_transaction(tx)

        receipt = self.web3_client.send_transaction(acc_in_container, instruction_tx)
        assert receipt["status"] == 1, "Transaction should be successful"

    def test_send_token_to_empty_to_field_by_acc_in_container(self, account_in_container):
        sender_account = account_in_container
        sender_balance = self.web3_client.get_balance(sender_account)

        self.web3_client.send_neon(sender_account, to=None, amount=1)
        assert sender_balance > self.web3_client.get_balance(sender_account)

    def test_solana_call_before_iterative_actions_by_acc_in_container(
        self,
        counter_resource_address: Pubkey,
        call_solana_caller,
        account_in_container,
    ):
        sender = account_in_container
        matrix_length = 15
        matrix = [[random.randint(1, 100) for _ in range(matrix_length)] for _ in range(matrix_length)]

        instruction = Instruction(
            program_id=COUNTER_ID,
            accounts=[
                AccountMeta(counter_resource_address, is_signer=False, is_writable=True),
            ],
            data=bytes([0x1]),
        )
        serialized = serialize_instruction(COUNTER_ID, instruction)

        tx = self.web3_client.make_raw_tx(sender.address)

        instruction_tx = call_solana_caller.functions.solanaCallBeforeActionWithMatrix(
            matrix, 0, serialized
        ).build_transaction(tx)

        resp = self.web3_client.send_transaction(sender, instruction_tx)
        assert resp["status"] == 0, resp
