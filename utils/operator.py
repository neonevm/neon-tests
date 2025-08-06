import json
import os
import pathlib

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed, Commitment
from eth_keys import keys as eth_keys

from utils.consts import OPERATOR_KEYPAIR_PATH
from utils.evm_loader import EvmLoader
from utils.neon_layouts.operator_balance_account import OperatorBalanceAccount
from utils.web3client import Web3Client


class Operator:
    def __init__(
        self,
        evm_loader: EvmLoader,
    ):
        self.operator_keypairs = self.get_operator_keypairs()
        self.evm_loader = evm_loader

    @staticmethod
    def get_operator_keypairs():
        directory = OPERATOR_KEYPAIR_PATH
        operator_keys = []
        for key in os.listdir(directory):
            key_file = pathlib.Path(f"{directory}/{key}")
            with open(key_file, "r") as f:
                secret_key = json.load(f)
                account = Keypair.from_bytes(secret_key)
                operator_keys.append(account)
        return operator_keys

    def get_operator_balance_account(self, operator: Keypair, w3_client):
        operator_ether = eth_keys.PrivateKey(operator.secret()[:32]).public_key.to_canonical_address()
        seed_version = bytes("\3", encoding="utf-8").decode("unicode-escape").encode("utf-8")
        operator_pubkey_bytes = bytes(operator.pubkey())

        seed_list = (
            seed_version,
            operator_pubkey_bytes,
            operator_ether,
            w3_client.chain_id.to_bytes(32, byteorder="big"),
        )
        balance_account, _ = Pubkey.find_program_address(seed_list, self.evm_loader.loader_id)
        return balance_account

    def get_solana_balance(self):
        balances = []
        for keypair in self.operator_keypairs:
            balance = self.evm_loader.get_balance(keypair.pubkey(), commitment=Confirmed)
            if isinstance(balance, dict):
                balance = balance["result"]["value"]
            else:
                balance = balance.value
            balances.append(balance)
        return sum(balances)

    def get_token_balance(self, w3_client: Web3Client):
        balances = []
        for operator in self.operator_keypairs:
            token_addr = self.get_operator_balance_account(operator, w3_client)
            info: bytes = self.evm_loader.get_account_info(token_addr, commitment=Commitment("confirmed")).value.data
            amount = OperatorBalanceAccount(info).balance
            balances.append(amount)
        return sum(balances)
