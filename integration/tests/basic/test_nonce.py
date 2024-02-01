import random
import time

import allure
import pytest

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.assert_message import ErrorMessage
from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.apiclient import wait_finalized_block


@allure.feature("Ethereum compatibility")
@allure.story("Verify mempool and how proxy handle nonce")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestNonce:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    TRANSFER_CNT = 25

    def check_transaction_list(self, tx_hash_list):
        for tx_hash in tx_hash_list:
            tx_receipt = self.web3_client.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            assert tx_receipt["status"] == 1

    def test_get_receipt_sequence(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_hash_list = []
        for i in range(self.TRANSFER_CNT):
            res = self.web3_client.send_neon(sender_account, recipient_account, 0.1)
            tx_hash_list.append(res["transactionHash"].hex())

        self.check_transaction_list(tx_hash_list)

    def test_reverse_sequence(self):
        sender_account = self.accounts[0]
        nonce = self.web3_client.get_nonce(sender_account.address)
        nonce_list = [i for i in range(nonce + self.TRANSFER_CNT - 1, nonce - 1, -1)]

        tx_hash_list = []
        for nonce in nonce_list:
            transaction = self.web3_client.make_raw_tx(sender_account, nonce=nonce, estimate_gas=True)
            signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
            tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_list.append(tx.hex())

        self.check_transaction_list(tx_hash_list[::-1])

    def test_random_sequence(self):
        sender_account = self.accounts[0]
        nonce = self.web3_client.get_nonce(sender_account.address)
        nonce_list = [i for i in range(nonce, nonce + self.TRANSFER_CNT)]
        random.shuffle(nonce_list)
        tx_hash_list = []
        for nonce in nonce_list:
            transaction = self.web3_client.make_raw_tx(sender_account, nonce=nonce, estimate_gas=True)
            signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
            tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_list.append(tx.hex())

        self.check_transaction_list(tx_hash_list)

    def test_send_transaction_with_low_nonce_after_several_high(self, json_rpc_client):
        """Check that transaction with a higher nonce is waiting for its turn in the mempool"""
        sender_account = self.accounts[0]
        nonce = self.web3_client.eth.get_transaction_count(sender_account.address)
        trx = {}
        for n in [nonce + 3, nonce + 1, nonce]:
            transaction = self.web3_client.make_raw_tx(sender_account, nonce=n, estimate_gas=True)
            signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
            response_trx = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
            trx[n] = response_trx

        receipt_trx1 = json_rpc_client.send_rpc(method="eth_getTransactionReceipt", params=[trx[n + 3]["result"]])
        assert receipt_trx1["result"] is None, "Transaction shouldn't be accepted"

        transaction = self.web3_client.make_raw_tx(sender_account, nonce=n + 2, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])

        tx_receipt = self.web3_client.eth.wait_for_transaction_receipt(trx[n + 3]["result"], timeout=120)
        assert tx_receipt is not None, "Transaction should be accepted"

    def test_send_transaction_with_low_nonce_after_high(self, json_rpc_client):
        """Check that transaction with a higher nonce is waiting for its turn in the mempool"""
        sender_account = self.accounts[0]
        nonce = self.web3_client.eth.get_transaction_count(sender_account.address) + 1
        transaction = self.web3_client.make_raw_tx(sender_account, nonce=nonce, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response_trx1 = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])

        time.sleep(10)  # transaction with n+1 nonce should wait when transaction with nonce = n will be accepted
        receipt_trx1 = json_rpc_client.send_rpc(method="eth_getTransactionReceipt", params=[response_trx1["result"]])
        assert receipt_trx1["result"] is None, "Transaction shouldn't be accepted"

        transaction = self.web3_client.make_raw_tx(sender_account, nonce=nonce - 1, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response_trx2 = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        for result in (response_trx2["result"], response_trx1["result"]):
            self.web3_client.wait_for_transaction_receipt(result)
            assert rpc_checks.is_hex(result)

    def test_send_transaction_with_the_same_nonce_and_lower_gas(self, json_rpc_client):
        """Check that transaction with a low gas and the same nonce can't be sent"""
        sender_account = self.accounts[0]
        nonce = self.web3_client.eth.get_transaction_count(sender_account.address) + 1
        gas = self.web3_client.gas_price()
        transaction = self.web3_client.make_raw_tx(sender_account, nonce=nonce, gas_price=gas, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        transaction = self.web3_client.make_raw_tx(sender_account, nonce=nonce, gas_price=gas - 1, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        assert "error" in response, f"Response doesn't has an error: {response}"
        assert ErrorMessage.REPLACEMENT_UNDERPRICED.value in response["error"]["message"]
        assert response["error"]["code"] == -32000

    def test_send_transaction_with_the_same_nonce_and_higher_gas(self, json_rpc_client):
        """Check that transaction with higher gas and the same nonce can be sent"""
        sender_account = self.accounts[0]
        nonce = self.web3_client.eth.get_transaction_count(sender_account.address) + 1
        gas = self.web3_client.gas_price()
        transaction = self.web3_client.make_raw_tx(sender_account, nonce=nonce, gas_price=gas, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        transaction = self.web3_client.make_raw_tx(sender_account, nonce=nonce, gas_price=gas * 10, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        assert "error" not in response
        assert "result" in response

    def test_send_the_same_transactions_if_accepted(self, json_rpc_client):
        """Transaction cannot be sent again if it was accepted"""
        sender_account = self.accounts[0]
        transaction = self.web3_client.make_raw_tx(sender_account, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        params = [signed_tx.rawTransaction.hex()]
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", params)
        receipt = self.web3_client.wait_for_transaction_receipt(response["result"])
        block_num = receipt["blockNumber"]
        wait_finalized_block(json_rpc_client, block_num)

        response = json_rpc_client.send_rpc("eth_sendRawTransaction", params)
        assert ErrorMessage.ALREADY_KNOWN.value in response["error"]["message"]
        assert response["error"]["code"] == -32000

    def test_send_the_same_transactions_if_not_accepted(self, json_rpc_client):
        """Transaction can be sent again if it was not accepted"""
        sender_account = self.accounts[0]
        transaction = self.web3_client.make_raw_tx(sender_account, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        params = [signed_tx.rawTransaction.hex()]
        json_rpc_client.send_rpc("eth_sendRawTransaction", params)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", params)
        assert "error" not in response
        assert "result" in response

    def test_send_transaction_with_old_nonce(self, json_rpc_client):
        """Check that transaction with old nonce can't be sent"""
        sender_account = self.accounts[0]
        nonce = self.web3_client.eth.get_transaction_count(sender_account.address)
        transaction = self.web3_client.make_raw_tx(sender_account, amount=1, nonce=nonce, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        assert response["result"] , f"Response doesn't have result field: {response}"
        receipt = self.web3_client.wait_for_transaction_receipt(response["result"])
        block_num = receipt["blockNumber"]
        wait_finalized_block(json_rpc_client, block_num)

        transaction = self.web3_client.make_raw_tx(sender_account, amount=2, nonce=nonce, estimate_gas=True)
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, sender_account.key)
        response = json_rpc_client.send_rpc("eth_sendRawTransaction", [signed_tx.rawTransaction.hex()])
        assert ErrorMessage.NONCE_TOO_LOW.value in response["error"]["message"]
        assert response["error"]["code"] == -32002

    @pytest.mark.multipletokens
    def test_nonce_with_several_chains(self, class_account_sol_chain, web3_client_sol, faucet):
        recipient_account = self.accounts[1]
        sender = class_account_sol_chain
        faucet.request_neon(sender.address, 100)
        neon_chain_nonce = self.web3_client.get_nonce(sender.address)
        sol_chain_nonce = web3_client_sol.get_nonce(sender.address)
        transaction_order_list = ["sol", "neon", "sol", "sol", "sol", "neon"]

        for item in transaction_order_list:
            client = web3_client_sol if item == "sol" else self.web3_client
            client.send_tokens(sender, recipient_account, 1000)
        assert self.web3_client.get_nonce(sender.address) == neon_chain_nonce + 2
        assert web3_client_sol.get_nonce(sender.address) == sol_chain_nonce + 4
