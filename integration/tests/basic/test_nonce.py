import random
import time

import allure

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.assert_message import ErrorMessage
from integration.tests.basic.helpers.basic import BaseMixin


@allure.story("Verify mempool and how proxy handle nonce")
class TestNonce(BaseMixin):
    TRANSFER_CNT = 25

    def check_transaction_list(self, tx_hash_list):
        for tx_hash in tx_hash_list:
            tx_receipt = self.wait_transaction_accepted(tx_hash, timeout=30)
            assert tx_receipt["result"]["status"] == "0x1"

    def test_get_receipt_sequence(self):
        tx_hash_list = []
        for i in range(self.TRANSFER_CNT):
            res = self.send_neon(self.sender_account, self.recipient_account, 0.1)
            tx_hash_list.append(res["transactionHash"].hex())

        self.check_transaction_list(tx_hash_list)

    def test_reverse_sequence(self):
        nonce = self.web3_client.get_nonce(self.sender_account.address)
        nonce_list = [i for i in range(nonce + self.TRANSFER_CNT - 1, nonce - 1, -1)]

        tx_hash_list = []
        for nonce in nonce_list:
            transaction = self.create_tx_object(nonce=nonce)
            signed_tx = self.web3_client.eth.account.sign_transaction(
                transaction, self.sender_account.key
            )
            tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_list.append(tx.hex())

        self.check_transaction_list(tx_hash_list[::-1])

    def test_random_sequence(self):
        nonce = self.web3_client.get_nonce(self.sender_account.address)
        nonce_list = [i for i in range(nonce, nonce + self.TRANSFER_CNT)]
        random.shuffle(nonce_list)
        tx_hash_list = []
        for nonce in nonce_list:
            transaction = self.create_tx_object(nonce=nonce)
            signed_tx = self.web3_client.eth.account.sign_transaction(
                transaction, self.sender_account.key
            )
            tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_list.append(tx.hex())

        self.check_transaction_list(tx_hash_list)

    def test_send_transaction_with_low_nonce_after_several_high(self):
        """Check that transaction with a higher nonce is waiting for its turn in the mempool"""
        nonce = self.web3_client.eth.get_transaction_count(self.sender_account.address)
        trx = {}
        for n in [nonce + 3, nonce + 1, nonce]:
            transaction = self.create_tx_object(nonce=n)
            signed_tx = self.web3_client.eth.account.sign_transaction(
                transaction, self.sender_account.key
            )
            response_trx = self.proxy_api.send_rpc(
                "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
            )
            trx[n] = response_trx

        time.sleep(
            15
        )  # transaction with n+3 nonce should wait when transaction with nonce = n+2 will be accepted
        receipt_trx1 = self.proxy_api.send_rpc(
            method="eth_getTransactionReceipt", params=[trx[n + 3]["result"]]
        )
        assert receipt_trx1["result"] is None, "Transaction shouldn't be accepted"

        transaction = self.create_tx_object(nonce=n + 2)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )

        tx_receipt = self.wait_transaction_accepted(trx[n + 3]["result"])
        assert tx_receipt["result"] is not None, "Transaction should be accepted"

    def test_send_transaction_with_low_nonce_after_high(self):
        """Check that transaction with a higher nonce is waiting for its turn in the mempool"""
        nonce = (
            self.web3_client.eth.get_transaction_count(self.sender_account.address) + 1
        )
        transaction = self.create_tx_object(nonce=nonce)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response_trx1 = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )

        time.sleep(
            10
        )  # transaction with n+1 nonce should wait when transaction with nonce = n will be accepted
        receipt_trx1 = self.proxy_api.send_rpc(
            method="eth_getTransactionReceipt", params=[response_trx1["result"]]
        )
        assert receipt_trx1["result"] is None, "Transaction shouldn't be accepted"

        transaction = self.create_tx_object(nonce=nonce - 1)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response_trx2 = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        for result in (response_trx2["result"], response_trx1["result"]):
            self.wait_transaction_accepted(result)
            assert rpc_checks.is_hex(result)

    def test_send_transaction_with_the_same_nonce_and_lower_gas(self):
        """Check that transaction with a low gas and the same nonce can't be sent"""
        nonce = (
            self.web3_client.eth.get_transaction_count(self.sender_account.address) + 1
        )
        gas = self.web3_client.gas_price()
        transaction = self.create_tx_object(nonce=nonce, gas_price=gas)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        transaction = self.create_tx_object(nonce=nonce, gas_price=gas - 1)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        assert (
            ErrorMessage.REPLACEMENT_UNDERPRICED.value in response["error"]["message"]
        )
        assert response["error"]["code"] == -32000

    def test_send_transaction_with_the_same_nonce_and_higher_gas(self):
        """Check that transaction with higher gas and the same nonce can be sent"""
        nonce = (
            self.web3_client.eth.get_transaction_count(self.sender_account.address) + 1
        )
        gas = self.web3_client.gas_price()
        transaction = self.create_tx_object(nonce=nonce, gas_price=gas)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        transaction = self.create_tx_object(nonce=nonce, gas_price=gas * 10)
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.sender_account.key
        )
        response = self.proxy_api.send_rpc(
            "eth_sendRawTransaction", [signed_tx.rawTransaction.hex()]
        )
        assert "error" not in response
        assert "result" in response
