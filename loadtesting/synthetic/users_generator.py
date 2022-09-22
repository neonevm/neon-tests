import os
# import time
# import random
# import base64
# from hashlib import sha256
import json
# from dataclasses import dataclass
#
import web3
import requests
# from eth_keys import keys as eth_keys
from solana.rpc.api import Client as SolanaClient
from solana.keypair import Keypair
from eth_keys import keys as eth_keys
# from solana.publickey import PublicKey
# from solana.rpc.types import TxOpts
# from solana.system_program import SYS_PROGRAM_ID
# from solana.transaction import AccountMeta, TransactionInstruction
# import helpers
#
#
# sol_client = SolanaClient("http://proxy.night.stand.neontest.xyz/node-solana")
web = web3.Web3()
#
#
# @dataclass
# class TreasuryPool:
#     index: int
#     account: PublicKey
#     buffer: bytes
#
#
# def create_operators():
#     operators = []
#     sol_client = SolanaClient("http://proxy.night.stand.neontest.xyz/node-solana")
#
#     for key_name in os.listdir('operator-keypairs'):
#         print(f"Work with key {key_name}")
#         with open(f'operator-keypairs/{key_name}') as f:
#             data = json.load(f)
#             key = Keypair(data[:32])
#             sol_client.request_airdrop(key.public_key, 10000)
#             operators.append(key)
#     return operators
#
#
# def create_treasury(count=100):
#     collateral_seed_prefix = "collateral_seed_"
#     pool_base = PublicKey("4sW3SZDJB7qXUyCYKA7pFL8eCTfm3REr8oSiKkww7MaT")
#     treasury = []
#     for i in range(count):
#         seed = collateral_seed_prefix + str(i)
#         address = PublicKey(sha256(bytes(pool_base) + bytes(seed, "utf8") + bytes(
#             PublicKey("53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io"))).digest())
#         index_buf = i.to_bytes(4, "little")
#         treasury.append(TreasuryPool(i, address, index_buf))
#     return treasury
#
#
# def ether2solana(eth_address: str):
#     if eth_address.startswith("0x"):
#         eth_address = eth_address[2:]
#     seed = [b'\1', bytes.fromhex(eth_address)]
#     pda, nonce = PublicKey.find_program_address(seed, PublicKey("53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io"))
#     return pda, nonce
#
#
# def _get_account_data(
#         account,
#         expected_length: int = helpers.ACCOUNT_INFO_LAYOUT.sizeof(),
# ) -> bytes:
#     """Request account info"""
#     resp = sol_client.get_account_info(account)["result"].get("value")
#     data = base64.b64decode(resp["data"][0])
#     if len(data) < expected_length:
#         raise Exception(f"Wrong data length for account data {account}")
#     return data
#
#
# def get_transaction_count(account) -> int:
#     """Get transactions count from account info"""
#     info = helpers.AccountInfo.from_bytes(_get_account_data(account))
#     return int.from_bytes(info.trx_count, "little")
#
#
# def make_eth_transaction(
#         to_addr: str,
#         signer: "eth_account.signers.local.LocalAccount",
#         nonce,
#         value: int = 0,
#         data: bytes = b"",
# ):
#     """Create eth transaction"""
#     tx = {
#         "to": to_addr,
#         "value": value,
#         "gas": 9999999999,
#         "gasPrice": 0,
#         "nonce": nonce,
#         "data": data,
#         "chainId": 111,
#     }
#     return web3.Web3().eth.account.sign_transaction(tx, signer.privateKey)
#
#
# def make_CreateAccountV02(
#         user_eth_account: "eth_account.account.LocalAccount",
#         user_account_bump: int,
#         operator: Keypair,
#         user_solana_account: PublicKey
# ):
#     code = 24
#     d = code.to_bytes(1, "little") + bytes.fromhex(user_eth_account.address[2:]) + user_account_bump.to_bytes(1,
#                                                                                                               "little")
#
#     accounts = [
#         AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
#         AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=True),
#         AccountMeta(pubkey=user_solana_account, is_signer=False, is_writable=True),
#     ]
#     return TransactionInstruction(program_id=PublicKey("53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io"), data=d,
#                                   keys=accounts)
#
#
# def make_TransactionExecuteFromInstruction(
#         instruction: bytes,
#         operator: Keypair,
#         treasury_address: PublicKey,
#         treasury_buffer: bytes,
#         additional_accounts,
# ):
#     """Create solana transaction instruction from eth transaction"""
#     code = 31
#     d = code.to_bytes(1, "little") + treasury_buffer + instruction
#     operator_ether_public = eth_keys.PrivateKey(operator.secret_key[:32]).public_key
#     operator_ether_solana = ether2solana(operator_ether_public.to_address())[0]
#
#     accounts = [
#         AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
#         AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
#         AccountMeta(pubkey=operator_ether_solana, is_signer=False, is_writable=True),
#         AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=True),
#         # Neon EVM account
#         AccountMeta(PublicKey("53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io"), is_signer=False, is_writable=False),
#     ]
#     for acc in additional_accounts:
#         accounts.append(
#             AccountMeta(acc, is_signer=False, is_writable=True),
#         )
#
#     return TransactionInstruction(program_id=PublicKey("53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io"), data=d,
#                                   keys=accounts)
#
#
# def generate_users(count=10000):
#     operators = create_operators()
#     treasury = create_treasury(100)
#
#     base_key = web.eth.account.create().privateKey.hex()
#     print(f"Main user private key: {base_key}")
#     main_user = web.eth.account.from_key(int(base_key, 16))
#
#     print(requests.post("http://proxy.night.stand.neontest.xyz/request_eth_token", json={"amount": 20000, "wallet": main_user.address}))
#     time.sleep(5)
#     main_user_solana_address = ether2solana(main_user.address)[0]
#     # main_nonce = get_transaction_count(main_user_solana_address)
#     main_nonce = 0
#     print(f"Main account nonce: {main_nonce}")
#
#     for i in range(count):
#         user = web.eth.account.from_key(int(base_key, 16) + 1 + i)
#         solana_address, bump = ether2solana(user.address)
#         operator = operators[random.randint(0, len(operators) - 1)]
#         treasury_pool = treasury[random.randint(0, len(treasury) - 1)]
#
#         create_acc = make_CreateAccountV02(
#             user, bump, operator, solana_address
#         )
#
#         eth_transaction = make_eth_transaction(
#             user.address,
#             data=b"",
#             signer=main_user,
#             value=100000000000,
#             nonce=main_nonce,
#         )
#
#         send_neon_instr = make_TransactionExecuteFromInstruction(
#             eth_transaction.rawTransaction,
#             operator,
#             treasury_pool.account,
#             treasury_pool.buffer,
#             [main_user_solana_address, solana_address],
#         )
#
#         tx = helpers.TransactionWithComputeBudget().add(create_acc)
#         tx.add(send_neon_instr)
#         t = sol_client.send_transaction(tx, operator, opts=TxOpts(
#             skip_confirmation=True, skip_preflight=True
#         ))
#         main_nonce += 1
#         time.sleep(1)
#         print(f"TX for {i} - {t}")

def create_operators():
    sol_client = SolanaClient("http://proxy.night.stand.neontest.xyz/node-solana")

    for key_name in os.listdir('operator-keypairs'):
        print(f"Work with key {key_name}")
        with open(f'operator-keypairs/{key_name}') as f:
            data = json.load(f)
            key = Keypair(data[:32])
            sol_client.request_airdrop(key.public_key, 10000)
            eth_address = eth_keys.PrivateKey(key.secret_key[:32]).public_key.to_address()
            resp = requests.post("http://proxy.night.stand.neontest.xyz/request_eth_token",
                                 json={"amount": 1000, "wallet": eth_address})
            print(f"Create operator {eth_address} - {key.public_key}")


def generate_user_faucet(count):
    base_key = web.eth.account.create().privateKey.hex()
    print(f"Main user private key: {base_key}")

    for i in range(count):
        user = web.eth.account.from_key(int(base_key, 16) + 1 + i)
        resp = requests.post("http://proxy.night.stand.neontest.xyz/request_eth_token",
                             json={"amount": 20000, "wallet": user.address})
        print(f"User addr: {user.address} - resp {resp.status_code}")


# generate_users(10000)
# generate_user_faucet(10000)
create_operators()