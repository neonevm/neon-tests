import os
# import time
# import random
# import base64
# from hashlib import sha256
import json
from concurrent.futures import ThreadPoolExecutor
# from dataclasses import dataclass
#
import web3
import requests
# from eth_keys import keys as eth_keys
from solana.rpc.api import Client as SolanaClient
from solana.keypair import Keypair
from eth_keys import keys as eth_keys


web = web3.Web3()
BASE_KEY = "0xc26286eebe70b838545855325d45b123149c3ca4a50e98b1fe7c7887e3327aa8"
FAUCET_URL = "http://3.13.67.238:3334/request_neon"
SOLANA_URL = "http://3.13.67.238:8899"


sol_client = SolanaClient(SOLANA_URL)


def create_operator(key):
    sol_client.request_airdrop(key.public_key, 10000)
    eth_address = eth_keys.PrivateKey(key.secret_key[:32]).public_key.to_address()
    resp = requests.post(FAUCET_URL,
                         json={"amount": 1000, "wallet": eth_address})
    print(f"Create operator {eth_address} - {key.public_key} ({resp.status_code})")


def create_operators():
    for key_name in os.listdir('operator-keypairs'):
        print(f"Work with key {key_name}")
        with ThreadPoolExecutor(max_workers=100) as executor:
            with open(f'operator-keypairs/{key_name}') as f:
                data = json.load(f)
                key = Keypair(data[:32])
            executor.submit(create_operator, key)


def generate_user_faucet(start_key: int, count):
    # base_key = web.eth.account.create().privateKey.hex()
    print(f"Main user private key: {start_key}")

    for i in range(0, count):
        user = web.eth.account.from_key(start_key + i)
        resp = requests.post(FAUCET_URL,
                             json={"amount": 20000, "wallet": user.address})
        print(f"User addr: {user.address} - resp {resp.status_code}")


def generate_faucet_users_parallel(workers=10, count=100000):
    users_count = count // workers
    keys = [int(BASE_KEY, 16) + o for o in range(0, count, users_count)]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for k in keys:
            executor.submit(generate_user_faucet, k, users_count)


create_operators()
generate_faucet_users_parallel(100, 100000)

