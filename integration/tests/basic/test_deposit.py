import json

from _pytest.config import Config
from solana.publickey import PublicKey
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.client import Token as SplToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (create_associated_token_account,
                                    get_associated_token_address)

import allure
from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import LAMPORT_PER_SOL
from utils.transfers_inter_networks import Transfer

wSOL = {
    "chain_id": 111,
    "address_spl": 'So11111111111111111111111111111111111111112',
    "address": '0x16869acc45BA20abEFB2DdE2096F66373fDe364F',
    "decimals": 9,
    "name": 'Wrapped SOL',
    "symbol": 'wSOL',
    "logo_uri": 'https://raw.githubusercontent.com/neonlabsorg/token-list/master/assets/solana-wsol-logo.svg'
}


@allure.feature("Ethereum compatibility")
@allure.story("Basic tests for deposit")
class TestDeposit(BaseMixin):
    def withdraw_neon(self, dest_acc, move_amount):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "NeonToken", "0.8.10", account=self.sender_account
        )

        instruction_tx = contract.functions.withdraw(
            bytes(dest_acc.public_key)
        ).build_transaction(
            {
                "from": self.sender_account.address,
                "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
                "gasPrice": self.web3_client.gas_price(),
                "value": self.web3_client._web3.to_wei(move_amount, "ether"),
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

    def send_tx_and_check_status_ok(self, tx, solana_account):
        opts = TxOpts(skip_preflight=True, skip_confirmation=False)
        sig = self.sol_client.send_transaction(
            tx, solana_account, opts=opts).value
        sig_status = json.loads(
            (self.sol_client.confirm_transaction(sig)).to_json())
        assert sig_status["result"]["value"][0]["status"] == {"Ok": None}

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

        tx = Transfer.neon_from_solana_to_neon_tx(solana_account,
                                                  neon_wallet,
                                                  neon_mint, 
                                                  new_account,
                                                  full_amount, 
                                                  evm_loader_id)
        self.send_tx_and_check_status_ok(tx, solana_account)

        neon_balance_after = self.get_balance_from_wei(new_account.address)
        assert neon_balance_after == neon_balance_before + amount

    def test_transfer_spl_token_from_solana_to_neon(self, solana_account, new_account, pytestconfig: Config, erc20_spl):
        evm_loader_id = pytestconfig.environment.evm_loader
        response = self.proxy_api.send_rpc(
            method="neon_getEvmParams", params=[])
        neon_pool_count = response["result"]["NEON_POOL_COUNT"]

        amount = 0.1
        full_amount = int(amount * LAMPORT_PER_SOL)

        mint_pubkey = PublicKey(wSOL['address_spl'])
        ata_address = get_associated_token_address(
            solana_account.public_key, mint_pubkey)

        self.create_ata(solana_account, mint_pubkey)

        spl_neon_token = SplToken(
            self.sol_client, mint_pubkey, TOKEN_PROGRAM_ID, solana_account)
        ata_balance_before = spl_neon_token.get_balance(
            ata_address, commitment=Commitment("confirmed"))

        # wrap SOL
        wrap_sol_tx = Transfer.wSOL_tx(self.sol_client, wSOL, full_amount,
                                       solana_account.public_key, ata_address)
        self.send_tx_and_check_status_ok(wrap_sol_tx, solana_account)

        ata_balance_after_wsol_tx = spl_neon_token.get_balance(
            ata_address, commitment=Commitment("confirmed"))

        # transfer wSOL
        transfer_tx = Transfer.neon_transfer_tx(
            self.web3_client, self.sol_client, full_amount, wSOL, solana_account,
            new_account, erc20_spl, evm_loader_id, neon_pool_count)
        self.send_tx_and_check_status_ok(transfer_tx, solana_account)

        ata_balance_after = spl_neon_token.get_balance(
            ata_address, commitment=Commitment("confirmed"))

        assert int(ata_balance_after.value.amount) == int(
            ata_balance_after_wsol_tx.value.amount) - amount == int(ata_balance_before.value.amount)
