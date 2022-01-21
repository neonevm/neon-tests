import json
import pathlib
from dataclasses import dataclass

import web3
import pytest
import solana
from _pytest.config import Config

from utils.operator import Operator
from utils.faucet import Faucet


@dataclass
class EnvironmentConfig:
    # name: str
    proxy_url: str
    solana_url: str
    faucet_url: str
    network_id: int
    operator_solana_key: str


def pytest_addoption(parser):
    parser.addoption(
        '--env', action='store', default='night-stand', help='Which stand use'
    )


def pytest_configure(config: Config):
    env_name = config.getoption("--env")
    with open(pathlib.Path().parent.parent / 'envs.json', 'r+') as f:
        environments = json.load(f)
    assert env_name in environments, f"Environment {env_name} doesn't exist in envs.json"
    config.environment = EnvironmentConfig(**environments[env_name])


@pytest.fixture(scope="session", autouse=True)
def operator(pytestconfig: Config):
    return Operator(
        pytestconfig.environment.proxy_url,
        pytestconfig.environment.solana_url,
        pytestconfig.environment.network_id,
        pytestconfig.environment.operator_solana_key
    )


@pytest.fixture(scope="session", autouse=True)
def faucet(pytestconfig: Config):
    return Faucet(pytestconfig.environment.faucet_url)


@pytest.fixture(scope="session", autouse=True)
def web3_client(pytestconfig: Config):
    client = web3.Web3(web3.HTTPProvider(pytestconfig.environment.proxy_url))
    return client


@pytest.fixture(scope="session", autouse=True)
def sol_client(pytestconfig: Config):
    client = solana.rpc.api.Client(pytestconfig.environment.solana_url)
    return client
