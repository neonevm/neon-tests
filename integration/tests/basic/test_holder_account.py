import json
import pathlib

from random import randrange

import pytest
import solana
from hashlib import sha256
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed
from solders.transaction_status import InstructionErrorFieldless


from integration.tests.basic.helpers.basic import BaseMixin
from utils import helpers
from utils.solana_client import SolanaClient


class TestHolderAccount(BaseMixin):

    @pytest.fixture(scope="session")
    def operator_keypair(self, sol_client) -> Keypair:
        with open(pathlib.Path().parent.parent / "operator1-keypair.json", "r") as key:
            account = Keypair(json.load(key)[:32]).generate()
        sol_client.request_airdrop(account.public_key, 10000000000)
        return account

    def test_create_holder_account(self, sol_client, operator_keypair):
        holder_acc, _ = sol_client.create_holder(operator_keypair)
        info = sol_client.get_account_info(PublicKey(holder_acc), commitment=Confirmed)
        assert info.value is not None, "Holder account is not created"
        assert info.value.lamports == 1000000000, "Account balance is not correct"

    def test_create_the_same_holder_account_by_another_user(self, sol_client, operator_keypair, pytestconfig):
        seed = str(randrange(1000000))
        user = Keypair.generate()
        sol_client.request_airdrop(user.public_key, 100000000000)
        evm_loader = PublicKey(pytestconfig.environment.evm_loader)
        storage = PublicKey(
            sha256(bytes(operator_keypair.public_key) + bytes(seed, 'utf8') + bytes(evm_loader)).digest())
        holder_acc, _ = sol_client.create_holder(operator_keypair, seed=seed, storage=storage)
        _, tx_sig_second_try = sol_client.create_holder(user, seed=seed, storage=storage)
        second_try_resp = sol_client.get_signature_statuses([tx_sig_second_try.value])
        info_acc = sol_client.get_account_info(PublicKey(holder_acc), commitment=Confirmed)
        assert info_acc.value is not None, "Holder account is not created"
        assert second_try_resp.value[0].status.err == InstructionErrorFieldless.AccountAlreadyInitialized, \
            f"Resp of second creation try hasn't AccountAlreadyInitialized error. Resp: {second_try_resp}"

    def test_write_tx_to_holder(self, sol_client: SolanaClient, operator_keypair):
        holder_acc, _ = sol_client.create_holder(operator_keypair)
        tx = self.create_tx_object(self.sender_account.address, self.recipient_account.address, amount=10)
        signed_tx = self.web3_client.eth.account.sign_transaction(tx, self.sender_account.key)
        sol_client.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        info = sol_client.get_account_info(holder_acc, commitment=Confirmed)
        assert signed_tx.rawTransaction == info.value.data[65:65 + len(signed_tx.rawTransaction)], \
            "Account data is not correct"

    def test_write_tx_to_holder_in_parts(self, sol_client: SolanaClient, operator_keypair):
        holder_acc, _ = sol_client.create_holder(operator_keypair)
        contract_interface = helpers.get_contract_interface('Fat', "0.8.10")
        contract = self.web3_client.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface["bin"])
        transaction = contract.constructor().buildTransaction(
            {
                "from": self.sender_account.address,
                "gasPrice": self.web3_client.gas_price(),
                "nonce": self.web3_client.get_nonce(self.sender_account),
            }
        )
        transaction["gas"] = self.web3_client.eth.estimate_gas(transaction)

        signed_tx = self.web3_client.eth.account.sign_transaction(transaction, self.sender_account.key)
        sol_client.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)
        info = sol_client.get_account_info(holder_acc, commitment=Confirmed)
        assert signed_tx.rawTransaction == info.value.data[65:65 + len(signed_tx.rawTransaction)], \
            "Account data is not correct"

    def test_write_tx_to_holder_by_no_owner(self, sol_client: SolanaClient, operator_keypair):
        holder_acc, _ = sol_client.create_holder(operator_keypair)
        user = Keypair.generate()
        sol_client.request_airdrop(user.public_key, 100000000000)

        tx = self.create_tx_object(self.sender_account.address, self.recipient_account.address, amount=100)
        signed_tx = self.web3_client.eth.account.sign_transaction(tx, self.sender_account.key)
        with pytest.raises(solana.rpc.core.RPCException, match="invalid account data for instruction"):
            sol_client.write_transaction_to_holder_account(signed_tx, holder_acc, user)

    def test_delete_holder(self, sol_client: SolanaClient, operator_keypair):
        holder_acc, _ = sol_client.create_holder(operator_keypair)
        sol_client.delete_holder(holder_acc, operator_keypair, operator_keypair)
        info = sol_client.get_account_info(holder_acc, commitment=Confirmed)
        assert info.value is None, "Holder account isn't deleted"

    def test_delete_holder_by_no_owner(self, sol_client: SolanaClient, operator_keypair):
        holder_acc, _ = sol_client.create_holder(operator_keypair)
        user = Keypair.generate()
        sol_client.request_airdrop(user.public_key, 100000000000)
        with pytest.raises(solana.rpc.core.RPCException, match="invalid account data for instruction"):
            sol_client.delete_holder(holder_acc, user, user)
