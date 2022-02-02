import json
import shutil
import pathlib
from dataclasses import dataclass

import web3
import pytest
import solana
from _pytest.config import Config

from utils.operator import Operator
from utils.faucet import Faucet
from utils.web3client import NeonWeb3Client


@dataclass
class EnvironmentConfig:
    # name: str
    proxy_url: str
    solana_url: str
    faucet_url: str
    network_id: int
    operator_solana_key: str
    spl_neon_mint: str


def pytest_addoption(parser):
    parser.addoption("--network", action="store", default="night-stand", help="Which stand use")


def pytest_configure(config: Config):
    env_name = config.getoption("--network")
    with open(pathlib.Path().parent.parent / "envs.json", "r+") as f:
        environments = json.load(f)
    assert env_name in environments, f"Environment {env_name} doesn't exist in envs.json"
    config.environment = EnvironmentConfig(**environments[env_name])


@pytest.fixture(scope="session", autouse=True)
def operator(pytestconfig: Config) -> Operator:
    return Operator(
        pytestconfig.environment.proxy_url,
        pytestconfig.environment.solana_url,
        pytestconfig.environment.network_id,
        pytestconfig.environment.operator_solana_key,
        pytestconfig.environment.spl_neon_mint,
    )


@pytest.fixture(scope="session", autouse=True)
def faucet(pytestconfig: Config) -> Faucet:
    return Faucet(pytestconfig.environment.faucet_url)


@pytest.fixture(scope="session", autouse=True)
def web3_client(pytestconfig: Config) -> NeonWeb3Client:
    client = NeonWeb3Client(pytestconfig.environment.proxy_url, pytestconfig.environment.network_id)
    return client


@pytest.fixture(scope="session", autouse=True)
def sol_client(pytestconfig: Config):
    client = solana.rpc.api.Client(pytestconfig.environment.solana_url)
    return client


@pytest.fixture(scope="session", autouse=True)
def allure_environment(pytestconfig: Config, web3_client: NeonWeb3Client):
    opts = {
        "Proxy.Version": web3_client.get_proxy_version()["result"],
        "EVM.Version": web3_client.get_evm_version()["result"],
        "CLI.Version": web3_client.get_cli_version()["result"]
    }

    allure_path = pytestconfig.getoption("--alluredir")

    yield opts
    with open(pathlib.Path() / allure_path / "environment.properties", "w+") as f:
        f.write("\n".join(map(lambda x: f"{x[0]}={x[1]}", opts.items())))
    categories_from = pathlib.Path() / "allure" / "categories.json"
    categories_to = pathlib.Path() / allure_path / "categories.json"
    shutil.copy(categories_from, categories_to)
