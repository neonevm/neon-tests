import pathlib
import random
import shutil
import string
import time

import allure
import pytest
import solana
import solana.rpc.api
from _pytest.config import Config
from solana.keypair import Keypair

from utils.erc20wrapper import ERC20Wrapper
from utils.faucet import Faucet
from utils.operator import Operator
from utils.web3client import NeonWeb3Client
from utils.apiclient import JsonRPCSession

LAMPORT_PER_SOL = 1_000_000_000
NEON_AIRDROP_AMOUNT = 10_000


def pytest_addoption(parser):
    parser.addoption("--network", action="store", default="night-stand", help="Which stand use")


@pytest.fixture(scope="session", autouse=True)
def faucet(pytestconfig: Config) -> Faucet:
    return Faucet(pytestconfig.environment.faucet_url)


@pytest.fixture(scope="session")
def json_rpc_client(pytestconfig: Config) -> JsonRPCSession:
    return JsonRPCSession(pytestconfig.environment.proxy_url)


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
        web3_client=web3_client,
    )


@pytest.fixture(scope="session", autouse=True)
def allure_environment(pytestconfig: Config, web3_client: NeonWeb3Client):
    opts = {
        "Proxy.Version": web3_client.get_proxy_version()["result"],
        "EVM.Version": web3_client.get_evm_version()["result"],
        "CLI.Version": web3_client.get_cli_version()["result"],
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
def prepare_account(operator, faucet, web3_client: NeonWeb3Client):
    """Create new account for tests and save operator pre/post balances"""
    with allure.step("Create account for tests"):
        acc = web3_client.eth.account.create()
    with allure.step(f"Request {NEON_AIRDROP_AMOUNT} NEON from faucet for {acc.address}"):
        faucet.request_neon(acc.address, NEON_AIRDROP_AMOUNT)
        assert web3_client.get_balance(acc) == NEON_AIRDROP_AMOUNT
    start_neon_balance = operator.get_neon_balance()
    start_sol_balance = operator.get_solana_balance()
    with allure.step(
            f"Operator initial balance: {start_neon_balance / LAMPORT_PER_SOL} NEON {start_sol_balance / LAMPORT_PER_SOL} SOL"
    ):
        pass
    yield acc
    end_neon_balance = operator.get_neon_balance()
    end_sol_balance = operator.get_solana_balance()
    with allure.step(
            f"Operator end balance: {end_neon_balance / LAMPORT_PER_SOL} NEON {end_sol_balance / LAMPORT_PER_SOL} SOL"
    ):
        pass
    with allure.step(f"Account end balance: {web3_client.get_balance(acc)} NEON"):
        pass


@pytest.fixture(scope="session")
def erc20wrapper(web3_client: NeonWeb3Client, faucet, pytestconfig: Config):
    wrapper = ERC20Wrapper(web3_client)
    eth_user = web3_client.create_account()

    faucet.request_neon(eth_user.address, 100)
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])

    contract, address = wrapper.deploy_wrapper(name=f"Test {symbol}", symbol=symbol, account=eth_user)

    contract = wrapper.get_wrapper_contract(address)

    wrapper.mint_tokens(eth_user, contract)

    yield contract, eth_user
