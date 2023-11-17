import typing as tp

import solana.rpc.api
from solana.publickey import PublicKey
from solana.rpc.commitment import Confirmed

from utils.web3client import NeonChainWeb3Client


class Operator:
    def __init__(
            self,
            proxy_url: str,
            solana_url: str,
            operator_neon_rewards_address: tp.List[str],
            neon_token_mint: str,
            operator_keys: tp.List[str],
            web3_client: tp.Optional[NeonChainWeb3Client] = None
    ):
        self._proxy_url = proxy_url
        self._solana_url = solana_url
        self._operator_neon_rewards_address = operator_neon_rewards_address
        self._neon_token_mint = neon_token_mint
        self._operator_keys = dict(zip(operator_keys, [None] * len(operator_keys)))
        self.web3 = web3_client
        if self.web3 is None:
            self.web3 = NeonChainWeb3Client(self._proxy_url)
        self.sol = solana.rpc.api.Client(self._solana_url)

    def get_solana_balance(self):
        balances = []
        for key in self._operator_keys:
            balance = self.sol.get_balance(PublicKey(key), commitment=Confirmed)
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
        if len(self._operator_neon_rewards_address) > 0:
            for addr in self._operator_neon_rewards_address:
                balances.append(w3_client.get_balance(w3_client.to_checksum_address(addr.lower())))
        return sum(balances)
