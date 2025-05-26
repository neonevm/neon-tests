import random

import pytest

from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client

"""
Test Objective:
    Ensure that no transactions fail during an EVM upgrade.

Test Procedure:
    1. Start the environment with the current versions of both the proxy and the EVM.
    2. Launch the test using multiple threads, each sending a stream of transactions.
    pytest ./integration/tests/migrations/test_evm_updating.py -c test_load_iterative_tx --numprocesses 7

    3. While the transactions are actively being sent, initiate an EVM upgrade.
    4. Confirm that:
        - The EVM upgrade completes successfully.
        - No transaction fails during or after the upgrade.

Expected Result:
    All transactions should be processed successfully, without errors or interruptions,
    even while the EVM is being updated.
"""


@pytest.mark.usefixtures("accounts", "web3_client")
@pytest.mark.neon_only
class TestEvmUpdating:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize("index", range(84))
    def test_load_iterative_tx(self, counter_contract, json_rpc_client, index, evm_loader):
        sender_account = self.accounts[random.randint(0, 7)]
        tx = self.web3_client.make_raw_tx(sender_account)

        instruction_tx = counter_contract.functions.moreInstructionWithLogs(0, 2000).build_transaction(tx)
        instruction_tx["gas"] = instruction_tx["gas"] * 10  # to prevent Out of gas error due to transactions restart
        resp = self.web3_client.send_transaction(sender_account, instruction_tx, timeout=180)
        print(resp["transactionHash"].hex())
        check_trx_is_success(self.web3_client, evm_loader, resp["transactionHash"].hex())
