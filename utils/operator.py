import time

import web3
import solana.rpc.api
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TokenAccountOpts


class Operator:
    def __init__(self, proxy_url: str, solana_url: str, network_id: int, solana_address: str, neon_token_mint: str):
        self._proxy_url = proxy_url
        self._solana_url = solana_url
        self._network_id = network_id
        self._solana_address = solana_address
        self._neon_token_mint = neon_token_mint
        self._neon_assoc_account_pubkey = None
        self.web3 = web3.Web3(web3.HTTPProvider(self._proxy_url))
        self.sol = solana.rpc.api.Client(self._solana_url)

    def get_solana_balance(self):
        return self.sol.get_balance(self._solana_address, commitment=Confirmed)["result"]["value"]

    def get_neon_balance(self):
        if self._neon_assoc_account_pubkey is None:
            accounts = self.sol.get_token_accounts_by_owner(
                self._solana_address, TokenAccountOpts(mint=self._neon_token_mint)
            )
            self._neon_assoc_account_pubkey = accounts["result"]["value"][0]["pubkey"]
        balance = self.sol.get_token_account_balance(self._neon_assoc_account_pubkey, commitment=Confirmed)
        return int(balance["result"]["value"]["amount"])

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