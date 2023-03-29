from _pytest.config import Config
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.instructions import create_associated_token_account

import allure
import json
from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import LAMPORT_PER_SOL


@allure.feature("Ethereum compatibility")
@allure.story("Basic tests for deposit")
class TestDeposit(BaseMixin):
    def withdraw_neon(self, dest_acc, move_amount):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "NeonToken", "0.8.10", account=self.sender_account
        )

        instruction_tx = contract.functions.withdraw(
            bytes(dest_acc.public_key)
        ).buildTransaction(
            {
                "from": self.sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
                "gasPrice": self.web3_client.gas_price(),
                "value": self.web3_client._web3.toWei(move_amount, "ether"),
            }
        )
        receipt = self.web3_client.send_transaction(
            self.sender_account, instruction_tx)
        assert receipt["status"] == 1

    def create_ata(self, solana_account, neon_mint):
        trx = Transaction()
        trx.add(
            create_associated_token_account(
                solana_account.public_key, solana_account.public_key, neon_mint
            )
        )
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        self.sol_client.send_transaction(trx, solana_account, opts=opts)

    def test_transfer_neon_from_solana_to_neon(self, new_account, solana_account, pytestconfig: Config, neon_mint):
        """Transfer Neon from Solana -> Neon"""
        amount = 0.1
        full_amount = int(amount * LAMPORT_PER_SOL)
        evm_loader_id = pytestconfig.environment.evm_loader

        neon_wallet = self.sol_client.get_neon_account_address(
            new_account.address, evm_loader_id)

        neon_balance_before = self.get_balance_from_wei(new_account.address)

        self.create_ata(solana_account, neon_mint)
        self.withdraw_neon(solana_account, amount)

        tx = self.sol_client.transaction_send_neon(
            solana_account, neon_wallet, neon_mint, new_account, full_amount, evm_loader_id)

        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        sig = self.sol_client.send_transaction(
            tx, solana_account, opts=opts).value
        sig_status = json.loads(
            (self.sol_client.confirm_transaction(sig)).to_json())
        assert sig_status["result"]["value"][0]["status"] == {"Ok": None}

        neon_balance_after = self.get_balance_from_wei(new_account.address)
        assert neon_balance_after == neon_balance_before + amount
