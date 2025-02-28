import json
import os

import web3
from web3.contract import Contract

from utils.accounts import EthAccounts
from utils.erc20 import ERC20
from utils.helpers import get_contract_interface


def k6_prepare_accounts(erc20, account_manager, users, balance, erc20_balance):
    print("Creating accounts...")
    accounts = {}

    # We create 2 accounts for each k6 virtual user: sender and receiver.
    # We need to create 2*VU accounts cause we want to make sure account's nonces is not overlapping.
    for i in range(int(users)):
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


def deploy_block_number_contract(
    eth_accounts: EthAccounts,
) -> Contract:
    print("Compiling BlockNumber contract...")
    contract_interface = get_contract_interface(
        "common/Block.sol",
        "0.8.12",
        contract_name="BlockNumber",
    )
    with open("./loadtesting/k6/contracts/BlockNumber/BlockNumber.abi", "wt") as f:
        json.dump(contract_interface["abi"], f)

    print("Deploying BlockNumber contract...")
    contract_owner = eth_accounts.create_account(balance=int(200))
    contract, contract_deploy_tx = eth_accounts._web3_client.deploy_and_get_contract(
        contract="Common/Block.sol",
        version="0.8.12",
        account=contract_owner,
        contract_name="BlockNumber",
    )
    print(f"Block contract deployed at {contract.address} with owner {contract_owner.address}")
    return contract


def k6_set_envs(network, erc20, users_number=None, initial_balance=None, bank_account=None):
    os.environ["K6_NETWORK"] = network
    os.environ["K6_USERS_NUMBER"] = users_number
    os.environ["K6_INITIAL_BALANCE"] = initial_balance

    if bank_account is not None:
        os.environ["K6_BANK_ACCOUNT"] = bank_account

    os.environ["K6_ERC20_ADDRESS"] = erc20.contract.address
    os.environ["K6_ERC20_OWNER"] = erc20.owner.address
