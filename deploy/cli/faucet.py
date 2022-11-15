from utils import web3client
from utils import faucet


def prepare_wallets_with_balance(settings, count=8, airdrop_amount=20000):
    print(f"Preparing {count} wallets with balances")
    web3_client = web3client.NeonWeb3Client(settings["proxy_url"], settings["network_id"])
    faucet_client = faucet.Faucet(settings["faucet_url"], web3_client)
    private_keys = []

    for i in range(count):
        acc = web3_client.eth.account.create()
        faucet_client.request_neon(acc.address, airdrop_amount)
        if i == 0:
            for _ in range(2):
                faucet_client.request_neon(acc.address, airdrop_amount)
        private_keys.append(acc.privateKey.hex())
    print("All private keys: ", ",".join(private_keys))
    return private_keys