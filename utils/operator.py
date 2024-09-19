import json
import os
import pathlib
import typing as tp

import solana.rpc.api
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed, Commitment
from eth_keys import keys as eth_keys

from utils.consts import OPERATOR_KEYPAIR_PATH
from utils.layouts import OPERATOR_BALANCE_ACCOUNT_LAYOUT
from utils.web3client import NeonChainWeb3Client


class Operator:
    def __init__(
            self,
            proxy_url: str,
            solana_url: str,
            neon_token_mint: str,
            web3_client: tp.Optional[NeonChainWeb3Client] = None,
            evm_loader: tp.Optional[str] = None
    ):
        self._proxy_url = proxy_url
        self._solana_url = solana_url
        self.operator_keypairs = self.get_operator_keypairs()
        self._neon_token_mint = neon_token_mint
        self.web3 = web3_client
        if self.web3 is None:
            self.web3 = NeonChainWeb3Client(self._proxy_url)
        self.sol = solana.rpc.api.Client(self._solana_url)
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
            w3_client.chain_id.to_bytes(32, byteorder="big"))
        balance_account, _ = Pubkey.find_program_address(seed_list, Pubkey.from_string(self.evm_loader))
        return balance_account

    def get_solana_balance(self):
        balances = []
        for keypair in self.operator_keypairs:
            balance = self.sol.get_balance(keypair.pubkey(), commitment=Confirmed)
            if isinstance(balance, dict):
                balance = balance["result"]["value"]
            else:
                balance = balance.value
            balances.append(balance)
        return sum(balances)

    def get_token_balance(self, w3_client=None):
        if w3_client is None:
            w3_client = self.web3
        balances = []
        for operator in self.operator_keypairs:
            token_addr = self.get_operator_balance_account(operator, w3_client)
            info: bytes = self.sol.get_account_info(token_addr, commitment=Commitment("confirmed")).value.data
            layout = OPERATOR_BALANCE_ACCOUNT_LAYOUT.parse(info)
            amount = int.from_bytes(layout.balance, byteorder="little")
            balances.append(amount)
        return sum(balances)
