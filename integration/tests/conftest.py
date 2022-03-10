import json
import shutil
import asyncio
import pathlib
import typing as tp
from dataclasses import dataclass

import web3
import allure
import pytest
import solana
from pythclient.pythaccounts import PythPriceAccount
from pythclient.solana import SolanaClient, SolanaPublicKey, SOLANA_MAINNET_HTTP_ENDPOINT
from _pytest.config import Config
from integration.tests.basic.helpers.json_rpc_requester import JsonRpcRequester

from utils.operator import Operator
from utils.faucet import Faucet
from utils.web3client import NeonWeb3Client


LAMPORT_PER_SOL = 1_000_000_000


@dataclass
class EnvironmentConfig:
    # name: str
    proxy_url: str
    solana_url: str
    faucet_url: str
    network_id: int
    operator_neon_rewards_address: tp.List[str]
    spl_neon_mint: str
    operator_keys: tp.List[str]


def pytest_addoption(parser):
    parser.addoption("--network", action="store", default="night-stand", help="Which stand use")


def pytest_configure(config: Config):
    env_name = config.getoption("--network")
    with open(pathlib.Path().parent.parent / "envs.json", "r+") as f:
        environments = json.load(f)
    assert env_name in environments, f"Environment {env_name} doesn't exist in envs.json"
    config.environment = EnvironmentConfig(**environments[env_name])


@pytest.fixture(scope="session")
def sol_price() -> float:
    async def get_price():
        account_key = SolanaPublicKey("H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG")
        solana_client = SolanaClient(endpoint=SOLANA_MAINNET_HTTP_ENDPOINT)
        price: PythPriceAccount = PythPriceAccount(account_key, solana_client)
        await price.update()
        return price.aggregate_price

    loop = asyncio.get_event_loop()
    price = loop.run_until_complete(get_price())
    with allure.step(f"SOL price {price}$"):
        return price


@pytest.fixture(scope="session", autouse=True)
def faucet(pytestconfig: Config) -> Faucet:
    return Faucet(pytestconfig.environment.faucet_url)

@pytest.fixture(scope="session", autouse=True)
def jsonrpc_requester(pytestconfig: Config) -> JsonRpcRequester:
    return JsonRpcRequester(pytestconfig.environment.proxy_url)


@pytest.fixture(scope="session", autouse=True)
def web3_client(pytestconfig: Config) -> NeonWeb3Client:
    client = NeonWeb3Client(pytestconfig.environment.proxy_url, pytestconfig.environment.network_id)
    return client


@pytest.fixture(scope="session", autouse=True)
def sol_client(pytestconfig: Config):
    client = solana.rpc.api.Client(pytestconfig.environment.solana_url)
    return client


@pytest.fixture(scope="session", autouse=True)
def operator(pytestconfig: Config, web3_client: NeonWeb3Client) -> Operator:
    return Operator(
        pytestconfig.environment.proxy_url,
        pytestconfig.environment.solana_url,
        pytestconfig.environment.network_id,
        pytestconfig.environment.operator_neon_rewards_address,
        pytestconfig.environment.spl_neon_mint,
        pytestconfig.environment.operator_keys,
        web3_client=web3_client
    )


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
        f.write("\n")
    categories_from = pathlib.Path() / "allure" / "categories.json"
    categories_to = pathlib.Path() / allure_path / "categories.json"
    shutil.copy(categories_from, categories_to)


@pytest.fixture(scope="class")
def prepare_account(operator, faucet, web3_client):
    """Create new account for tests and save operator pre/post balances"""
    with allure.step("Create account for tests"):
        acc = web3_client.eth.account.create()
    with allure.step(f"Request 1000 NEON from faucet for {acc.address}"):
        faucet.request_neon(acc.address, 1000)
        assert web3_client.get_balance(acc) == 1000
    start_neon_balance = operator.get_neon_balance()
    start_sol_balance = operator.get_solana_balance()
    with allure.step(f"Operator initial balance: {start_neon_balance / LAMPORT_PER_SOL} NEON {start_sol_balance / LAMPORT_PER_SOL} SOL"):
        pass
    yield acc
    end_neon_balance = operator.get_neon_balance()
    end_sol_balance = operator.get_solana_balance()
    with allure.step(f"Operator end balance: {end_neon_balance / LAMPORT_PER_SOL} NEON {end_sol_balance / LAMPORT_PER_SOL} SOL"):
        pass
    with allure.step(
            f"Account end balance: {web3_client.get_balance(acc)} NEON"):
        pass

