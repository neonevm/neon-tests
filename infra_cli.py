#!/usr/bin/env python3
import os
import re

import click
import requests
from deploy.cli import infrastructure
from deploy.cli.network_manager import NetworkManager
from utils import web3client
from utils.consts import EnvName

DOCKER_HUB_ORG_NAME = os.environ.get("DOCKER_HUB_ORG_NAME")
NEON_EVM_GITHUB_URL = f"https://api.github.com/repos/{DOCKER_HUB_ORG_NAME}/neon-evm"
PROXY_GITHUB_URL = f"https://api.github.com/repos/{DOCKER_HUB_ORG_NAME}/neon-proxy.py"
FAUCET_GITHUB_URL = f"https://api.github.com/repos/{DOCKER_HUB_ORG_NAME}/neon-faucet"
VERSION_BRANCH_TEMPLATE = r"[vt]{1}\d{1,2}\.\d{1,2}\.x.*"


def is_image_exist(image, tag):
    response = requests.get(
        url=f"https://registry.hub.docker.com/v2/repositories/{DOCKER_HUB_ORG_NAME}/{image}/tags/{tag}"
    )
    return response.status_code == 200


def is_branch_exist(endpoint, branch):
    if branch:
        response = requests.get(f"{endpoint}/branches/{branch}")
        if response.status_code == 200:
            return True
    else:
        return False


def define_stand_env_by_branch(current_branch, head_branch, base_branch):
    # use feature branch or version tag as tag for proxy, evm and faucet images or use latest
    proxy_tag, evm_tag, faucet_tag = "", "", ""

    if "/merge" not in current_branch and current_branch != "develop":
        branch_exists = is_branch_exist(PROXY_GITHUB_URL, current_branch)
        triggered_image_exist = is_image_exist("neon-proxy.py", f"evm-triggered-{current_branch}")
        if triggered_image_exist:
            proxy_tag = f"evm-triggered-{current_branch}"
        elif branch_exists:
            proxy_tag = current_branch
        else:
            proxy_tag = ""
        evm_tag = current_branch if is_branch_exist(NEON_EVM_GITHUB_URL, current_branch) else ""
        faucet_tag = current_branch if is_branch_exist(FAUCET_GITHUB_URL, current_branch) else ""
    elif head_branch:
        branch_exists = is_branch_exist(PROXY_GITHUB_URL, head_branch)
        triggered_image_exist = is_image_exist("neon-proxy.py", f"evm-triggered-{head_branch}")
        if triggered_image_exist:
            proxy_tag = f"evm-triggered-{head_branch}"
        elif branch_exists:
            proxy_tag = head_branch
        else:
            proxy_tag = ""
        evm_tag = head_branch if is_branch_exist(NEON_EVM_GITHUB_URL, head_branch) else ""
        faucet_tag = head_branch if is_branch_exist(FAUCET_GITHUB_URL, head_branch) else ""

    if re.match(VERSION_BRANCH_TEMPLATE, base_branch):
        version_branch = re.match(VERSION_BRANCH_TEMPLATE, base_branch)[0]
    elif re.match(VERSION_BRANCH_TEMPLATE, current_branch):
        version_branch = re.match(VERSION_BRANCH_TEMPLATE, current_branch)[0]
    else:
        version_branch = None

    if version_branch:
        proxy_tag = version_branch if is_branch_exist(PROXY_GITHUB_URL, version_branch) and not proxy_tag else proxy_tag
        evm_tag = version_branch if is_branch_exist(NEON_EVM_GITHUB_URL, version_branch) and not evm_tag else evm_tag
        faucet_tag = (
            version_branch if is_branch_exist(FAUCET_GITHUB_URL, version_branch) and not faucet_tag else faucet_tag
        )

    proxy_tag = "latest" if not proxy_tag else proxy_tag
    evm_tag = "latest" if not evm_tag else evm_tag
    faucet_tag = "latest" if not faucet_tag else faucet_tag

    evm_branch = evm_tag if evm_tag != "latest" else "develop"
    proxy_branch = proxy_tag if proxy_tag != "latest" and "evm-triggered-" not in proxy_tag else "develop"

    return {
        "evm_tag": evm_tag,
        "proxy_tag": proxy_tag,
        "faucet_tag": faucet_tag,
        "evm_branch": evm_branch,
        "proxy_branch": proxy_branch,
    }


@click.group()
def cli():
    pass


@cli.group("infra", help="Manage test infrastructure")
def infra():
    pass


@infra.command("get-stand-param")
@click.option("--current_branch", help="Branch of neon-tests repository")
@click.option("--head_branch", default="", help="Feature branch name")
@click.option("--base_branch", default="", help="Target branch of the pull request")
@click.option(
    "--param",
    default="",
    help="One of the stand param like evm_tag, " "proxy_tag, faucet_tag, evm_branch, proxy_branch",
)
def get_stand_param(current_branch, head_branch, base_branch, param):
    env = define_stand_env_by_branch(current_branch, head_branch, base_branch)
    print(env[param])
    return env[param]


@infra.command(name="gen-accounts", help="Setup accounts with balance")
@click.option("-c", "--count", default=2, help="How many users prepare")
@click.option("-a", "--amount", default=10000, help="How many airdrop")
@click.option("-n", "--network", default=EnvName.LOCAL, type=str, help="In which stand run tests")
def prepare_accounts(count, amount, network):
    infrastructure.prepare_accounts(network, count, amount)


@infra.command("print-network-param")
@click.option("-n", "--network", default=EnvName.LOCAL, type=str, help="In which stand run tests")
@click.option("-p", "--param", type=str, help="any network param like proxy_url, network_id e.t.c")
def print_network_param(network, param):
    network_manager = NetworkManager(network)
    print(network_manager.get_network_param(network, param))


infra.add_command(prepare_accounts, "gen-accounts")
infra.add_command(print_network_param, "print-network-param")


@cli.command(help="Get proxy version for the specified network")
@click.option("-n", "--network", type=click.Choice(EnvName), help="Network name")
def get_stand_proxy_version(network: EnvName):
    network_manager = NetworkManager()
    settings = network_manager.get_network_object(network.value)
    web3_client = web3client.NeonChainWeb3Client(settings["proxy_url"])
    response = web3_client.get_proxy_version()

    match = re.search(r"v\d+\.\d+\.\d+", response["result"])
    print(match.group(0))


if __name__ == "__main__":
    cli()
