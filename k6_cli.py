#!/usr/bin/env python3
import click
import subprocess
import sys
import os

from clickfile import catch_traceback

# K6-специфичные импорты
from utils.k6_helpers import k6_prepare_accounts, k6_set_envs, deploy_erc20_contract, deploy_block_number_contract
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client
from utils.faucet import Faucet
from deploy.cli.network_manager import NetworkManager


@click.group()
def k6():
    """Commands for k6 load tests."""


@k6.command("build", help="Build k6 executable file.")
@click.option("-t", "--tag", default="05e0ce5", help="Eth plugin tag or commit sha to use")
@catch_traceback
def build(tag):
    xk6_install = "go install go.k6.io/xk6/cmd/xk6@latest"
    xk6_build = f"xk6 build --with github.com/szkiba/xk6-prometheus --with github.com/neonlabsorg/xk6-ethereum@{tag}"

    command_install = subprocess.run(xk6_install, shell=True)

    if command_install.returncode != 0:
        sys.exit(command_install.returncode)

    command_build = subprocess.run(xk6_build, shell=True)
    if command_build.returncode != 0:
        sys.exit(command_build.returncode)


@k6.command("run", help="Run k6 performance test.")
@click.option("-n", "--network", required=True, default="local", help="Which network to use for envs assignment")
@click.option(
    "-s", "--script", required=True, default="./loadtesting/k6/tests/sendNeon.test.js", help="Path to k6 script"
)
@click.option(
    "-u", "--users", default=None, required=True, help="Number of users (have to be generated before load test run)"
)
@click.option("-b", "--balance", default=None, required=True, help="Initial balance of accounts in Neon")
@click.option("-a", "--bank_account", default=None, required=False, help="Eth bank account private key")
@catch_traceback
def run_load_k6(network, script, users, balance, bank_account):
    network_manager = NetworkManager()
    network_object = network_manager.get_network_object(network)
    web3_client = NeonChainWeb3Client(proxy_url=network_object["proxy_url"])
    faucet = Faucet(faucet_url=network_object["faucet_url"], web3_client=web3_client)
    account_manager = EthAccounts(web3_client, faucet, bank_account)

    print("Compiling ERC20 contract...")
    command_erc20 = "solc --abi ./contracts/EIPs/ERC20/ERC20.sol -o ./loadtesting/k6/contracts/ERC20 --overwrite"
    command_erc20_run = subprocess.run(command_erc20, shell=True)
    if command_erc20_run.returncode != 0:
        sys.exit(command_erc20_run.returncode)

    print("Deploying ERC20 contract...")
    erc20 = deploy_erc20_contract(web3_client, faucet, account_manager.create_account(balance=int(balance)))
    print(f"ERC20 contract deployed at {erc20.contract.address} with owner {erc20.owner.address}")

    block_contract = deploy_block_number_contract(account_manager)

    k6_prepare_accounts(erc20, account_manager, users, balance, 100)
    k6_set_envs(network, erc20, users, balance, bank_account)
    os.environ["K6_BLOCK_ADDRESS"] = block_contract.address

    command = f"./k6 run {script} -o 'prometheus=namespace=k6'"
    command_run = subprocess.run(command, shell=True)
    if command_run.returncode != 0:
        sys.exit(command_run.returncode)


if __name__ == "__main__":
    k6()
