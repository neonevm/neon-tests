import time
import typing as tp

import web3
import solana.rpc.api
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TokenAccountOpts

from utils.web3client import NeonWeb3Client


class Operator:
    def __init__(
            self,
            proxy_url: str,
            solana_url: str,
            network_id: int,
            operator_neon_rewards_address: tp.List[str],
            neon_token_mint: str,
            operator_keys: tp.List[str],
            web3_client: NeonWeb3Client
    ):
        self._proxy_url = proxy_url
        self._solana_url = solana_url
        self._network_id = network_id
        self._operator_neon_rewards_address = operator_neon_rewards_address
        self._neon_token_mint = neon_token_mint
        self._operator_keys = dict(zip(operator_keys, [None]*len(operator_keys)))
        self.web3 = web3_client
        self.sol = solana.rpc.api.Client(self._solana_url)

    def get_solana_balance(self):
        balances = []
        for key in self._operator_keys:
            balances.append(self.sol.get_balance(key, commitment=Confirmed)["result"]["value"])
        return sum(balances)

    def get_neon_balance(self):
        balances = []
        if len(self._operator_neon_rewards_address) > 0:
            for addr in self._operator_neon_rewards_address:
                balances.append(
                    self.web3.get_balance(
                        self.web3.toChecksumAddress(addr.lower())
                    )
                )
        else:
            for key in self._operator_keys:
                if self._operator_keys[key] is None:
                    accounts = self.sol.get_token_accounts_by_owner(
                        key, TokenAccountOpts(mint=self._neon_token_mint)
                    )
                    self._operator_keys[key] = accounts["result"]["value"][0]["pubkey"]
                balances.append(int(self.sol.get_token_account_balance(self._operator_keys[key], commitment=Confirmed)["result"]["value"]["amount"]))
        return sum(balances)

    def wait_solana_balance_changed(self, current_balance, timeout=90):
        """solana change balance only when blocks confirmed"""
        started = time.time()

        while (time.time() - started) < timeout:
            balance = self.get_solana_balance()
            if balance != current_balance:
                return balance
            time.sleep(5)
        raise TimeoutError(f"Operator solana balance didn't change for {timeout} seconds")

    def wait_neon_balance_changed(self, current_balance, timeout=90):
        """solana change balance only when blocks confirmed"""
        started = time.time()

        while (time.time() - started) < timeout:
            balance = self.get_neon_balance()
            if balance != current_balance:
                return balance
            time.sleep(5)
        raise TimeoutError(f"Operator neon balance didn't change for {timeout} seconds")