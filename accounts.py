import random
import requests
from utils.web3client import NeonWeb3Client


web_cli = NeonWeb3Client("http://142.132.165.47:9090/solana", 111)

users = [
    "0x0c19062861650faac0a7d290ca87e740de4abf0380096a3f3540530f89048e73",
    "0x9d634a20f852e4797f5497de2f68e8c942262e1976e709553bbcd30f98f2c76b",
    "0x5a312b14a2d00e6d6c02f0c8bfc2fe8da6f63f067c220025b721b17abe616e86",
    "0x1b5095bd6b3251919a989f365fe9e0b0ead33bb19abb1b20f50ed8cc7e87bb88",
    "0x80219d3582bc93d834267702ad276fc1bfa3928159c50f8d8bdbb7274bf4f542",
    "0x73f0bb98e5c798ef3cfc82c3294d965ed03715c40a874667b0d14cee2f50ca3c",
    "0x254e72a34c40c91b7cddc4764dd39077751869df05f0939f113ff13c341e28e0",
    "0x060e6332aedd54a6adc5ef7d9b354692f0e53d82543602d7ee9bab9ff53aaf10",
    "0x341fbca2e974fb302b4ddaf441acaf57923cac27c83a1072a7576cdc867a383e",
    "0x74ede3ffc77b51ace90fd4ce0f8738c34e4796a3aa02171c807b5adf1723c0c5",
    "0xf5f48e2d9843e8a18a4aa177bb9a7e9e25989e8632df21ddabc9fe9e4c59bada",
    "0x80b98ca17674861aa08b08c1b58781c9e82c913b6e387e58094123128b43b2a3",
    "0xc65764b8fa57e60b42e78a5b03f4ea7a793efee60108f8715bb868076740c87a",
    "0x8f1c49fad44cb0fd4199cef422f2827295c52281957ce5e332cd91c68b70e5cd",
    "0xdef27a2b6bb58bf6cbfd58b4606ddee0b0fd2ffae70cf8953a75237557b6e623",
    "0xb8ca5c2aecbf13df170b13724b8ce620067199e629aed1926a0a6e8d75ee21d0"
]


print("--- Get user balances")
for user in users:
    u = web_cli._web3.eth.account.from_key(user)
    balance = web_cli.get_balance(u.address)
    print(f"Account {u.address} balance = {balance} and nonce {web_cli.get_nonce(u.address)}")

print("--- Airdrop for accounts")
for user in users:
    u = web_cli._web3.eth.account.from_key(user)
    requests.post("http://142.132.165.47:3333/request_neon", json={"amount": 10000, "wallet": u.address})

print("--- Deploy simple contracts by each account")
for user in users:
    u = web_cli._web3.eth.account.from_key(user)
    contract, receipt = web_cli.deploy_and_get_contract(
        random.choice(["Counter", "Fat", "IncreaseStorage"]),
        version="0.8.10",
        account=u
    )
    print(f"Deployed contract address: {receipt['contractAddress']}")

print("--- Monkey transfers to different accounts (100 iterations)")
for _ in range(100):
    u = web_cli._web3.eth.account.from_key(random.choice(users))
    new_user = web_cli._web3.eth.account.from_key(random.choice(users)).address
    amount = random.randint(0, 5)
    tx = web_cli.send_neon(u, new_user, amount)
    print(f"Send neon from {u.address} to {new_user} - {amount}")

print("--- Final user balances")
for user in users:
    u = web_cli._web3.eth.account.from_key(user)
    balance = web_cli.get_balance(u.address)
    print(f"Account {u.address} balance = {balance} and nonce {web_cli.get_nonce(u.address)}")
