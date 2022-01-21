import pytest

import web3

from ..base import BaseTests


class TestEconomics(BaseTests):
    @pytest.mark.only_stands
    def test_account_creation(self):
        balance_before = self.operator.get_solana_balance()
        acc = self.web3_client.eth.account.create()
        assert self.web3_client.eth.get_balance(acc.address) == 0
        balance_after = self.operator.get_solana_balance()
        assert balance_before > balance_after, "Operator balance after getBalance doesn't changed"

    def test_neon_transaction_to_account(self):
        print(self.web3_client.eth.gas_price)
        balance_before = self.operator.get_solana_balance()
        acc1 = self.web3_client.eth.account.create()
        acc2 = self.web3_client.eth.account.create()
        assert self.web3_client.eth.get_balance(acc1.address) == 0
        assert self.web3_client.eth.get_balance(acc2.address) == 0
        self.faucet.request_neon(acc1.address, 100)
        assert web3.Web3.fromWei(self.web3_client.eth.get_balance(acc1.address), "ether") == 100
        transaction = {
            "to": acc2.address,
            "value": 5,
            "chainId": self.operator._network_id,
            "gasPrice": self.web3_client.eth.gas_price,
            "gas": 10,
            "nonce": self.web3_client.eth.get_transaction_count(acc1.address)
        }
        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, acc1.key)
        self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        assert web3.Web3.fromWei(self.web3_client.eth.get_balance(acc1.address), "ether") == 90
        assert web3.Web3.fromWei(self.web3_client.eth.get_balance(acc2.address), "ether") == 10
        balance_after = self.operator.get_solana_balance()
        assert balance_before > balance_after, "Operator balance after getBalance doesn't changed"

    def test_spl_transaction(self):
        pass

    def test_erc20_transaction(self):
        pass
