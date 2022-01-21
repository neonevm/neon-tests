import web3
import solana.rpc.api


class Operator:
    def __init__(self, proxy_url: str, solana_url: str, network_id: int, solana_address: str):
        self._proxy_url = proxy_url
        self._solana_url = solana_url
        self._network_id = network_id
        self._solana_address = solana_address
        self.web3 = web3.Web3(web3.HTTPProvider(self._proxy_url))
        self.sol = solana.rpc.api.Client(self._solana_url)

    def get_solana_balance(self):
        return self.sol.get_balance(self._solana_address)["result"]["value"]

    def get_neon_balance(self):
        pass
