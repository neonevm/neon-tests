import os
import typing as tp

from deploy.cli import faucet as faucet_cli
from deploy.cli.network_manager import NetworkManager


def set_github_env(envs: tp.Dict, upper=True) -> None:
    """Set environment for github action"""
    path = os.getenv("GITHUB_ENV", str())
    if os.path.exists(path):
        with open(path, "a") as env_file:
            for key, value in envs.items():
                env_file.write(f"\n{key.upper() if upper else key}={str(value)}")


def prepare_accounts(network_name, count, amount) -> tp.List:
    network_manager = NetworkManager(network_name)
    network = network_manager.get_network_object(network_name)
    accounts = faucet_cli.prepare_wallets_with_balance(network, count, amount)
    if os.environ.get("CI"):
        set_github_env(dict(accounts=",".join(accounts)))
    return accounts
