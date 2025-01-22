import json
import os
import web3
from utils.erc20 import ERC20


def k6_prepare_accounts(erc20, account_manager, users, balance, erc20_balance):
    print("Creating accounts...")
    accounts = {}

    # We create 2 accounts for each k6 virtual user: sender and receiver.
    # We need to create 2*VU accounts cause we want to make sure account's nonces is not overlapping.
    for i in range(2 * int(users)):
        account_sender = account_manager.create_account(balance=int(balance))
        account_receiver = account_manager.create_account(balance=0)
        accounts[i] = {
            "sender_address": str(account_sender.address),
            "sender_key": str(account_sender.key.hex())[2:],
            "receiver_address": str(account_receiver.address),
        }

        tx_receipt = erc20.transfer(erc20.owner, account_sender, erc20_balance)
        assert tx_receipt["status"] == 1, "ERC20 transfer failed"
        print(
            f"Account {str(i)} sender: {account_sender.address}, initial balance: {balance} Neon, {erc20_balance} ERC20."
        )
        print(f"Account {str(i)} receiver: {account_receiver.address}")

    with open("./loadtesting/k6/data/accounts.json", "w", encoding="utf-8") as f:
        json.dump(accounts, f)


def deploy_erc20_contract(web3_client, faucet, account):
    return ERC20(
        web3_client,
        faucet,
        owner=account,
        amount=web3.Web3.to_wei(10000000000, "ether"),
    )


def k6_set_envs(network, erc20, users_number=None, initial_balance=None, bank_account=None):
    os.environ["K6_NETWORK"] = network
    os.environ["K6_USERS_NUMBER"] = users_number
    os.environ["K6_INITIAL_BALANCE"] = initial_balance

    if bank_account is not None:
        os.environ["K6_BANK_ACCOUNT"] = bank_account

    os.environ["K6_ERC20_ADDRESS"] = erc20.contract.address
    os.environ["K6_ERC20_OWNER"] = erc20.owner.address
