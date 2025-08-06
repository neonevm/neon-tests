from utils import faucet
from eth_account import Account


def prepare_wallets_with_balance(settings, count=8, airdrop_amount=20000):
    print(f"Preparing {count} wallets with balances")
    faucet_client = faucet.Faucet(settings["faucet_url"])
    private_keys = []

    for i in range(count):
        acc = Account.create()
        faucet_client.request_neon(acc.address, airdrop_amount)
        if i == 0:
            for _ in range(2):
                faucet_client.request_neon(acc.address, airdrop_amount)
        private_keys.append(acc.key.hex())
    print("All private keys: ", ",".join(private_keys))
    return private_keys
