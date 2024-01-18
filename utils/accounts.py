from .web3client import NeonChainWeb3Client


class EthAccounts:
    def __init__(self, web3_client: NeonChainWeb3Client, faucet, eth_bank_account):
        self._web3_client = web3_client
        self._faucet = faucet
        self._bank_account = eth_bank_account
        self._accounts = []

    def __getitem__(self, item):
        if len(self._accounts) < (item + 1):
            for _ in range(item + 1 - len(self._accounts)):
                account = self._web3_client.create_account_with_balance(self._faucet, bank_account=self._bank_account)

                self._accounts.append(account)
        return self._accounts[item]
