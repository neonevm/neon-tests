import json
import os
import pathlib
import random
import shutil
import typing as tp
import string

import allure
import base58
import pytest
from _pytest.config import Config
from solana.keypair import Keypair
from solana.publickey import PublicKey

from utils.consts import LAMPORT_PER_SOL
from utils.erc20wrapper import ERC20Wrapper
from utils.faucet import Faucet
from utils.operator import Operator
from utils.web3client import NeonWeb3Client
from utils.apiclient import JsonRPCSession
from utils.solana_client import SolanaClient

NEON_AIRDROP_AMOUNT = 10_000


def pytest_collection_modifyitems(config, items):
    deselected_items = []
    selected_items = []
    if config.getoption("--network") == "devnet":
        deselected_mark = "only_stands"
    else:
        deselected_mark = "only_devnet"

    for item in items:
        if item.get_closest_marker(deselected_mark):
            deselected_items.append(item)
        else:
            selected_items.append(item)

    config.hook.pytest_deselected(items=deselected_items)
    items[:] = selected_items


@pytest.fixture(scope="session", autouse=True)
def faucet(pytestconfig: Config, web3_client) -> Faucet:
    return Faucet(pytestconfig.environment.faucet_url, web3_client)


@pytest.fixture(scope="session")
def json_rpc_client(pytestconfig: Config) -> JsonRPCSession:
    return JsonRPCSession(pytestconfig.environment.proxy_url)


@pytest.fixture(scope="session", autouse=True)
def web3_client(pytestconfig: Config) -> NeonWeb3Client:
    client = NeonWeb3Client(
        pytestconfig.environment.proxy_url, pytestconfig.environment.network_id
    )
    return client


@pytest.fixture(scope="session", autouse=True)
def sol_client(pytestconfig: Config):
    client = SolanaClient(
        pytestconfig.environment.solana_url,
        pytestconfig.environment.account_seed_version,
    )
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
        "Network": pytestconfig.environment.proxy_url,
        "Proxy.Version": web3_client.get_proxy_version()["result"],
        "EVM.Version": web3_client.get_evm_version()["result"],
        "CLI.Version": web3_client.get_cli_version()["result"],
    }

    yield opts

    allure_dir = pytestconfig.getoption("--alluredir")
    allure_path = pathlib.Path() / allure_dir
    with open(allure_path / "environment.properties", "w+") as f:
        f.write("\n".join(map(lambda x: f"{x[0]}={x[1]}", opts.items())))
        f.write("\n")
    categories_from = pathlib.Path() / "allure" / "categories.json"
    categories_to = allure_path / "categories.json"
    shutil.copy(categories_from, categories_to)

    if "CI" in os.environ:
        with open(allure_path / "executor.json") as f:
            json.dump(
                {
                    "name": "Github Action",
                    "type": "github",
                    "url": "https://github.com/neonlabsorg/neon-tests/actions",
                    "buildOrder": os.environ.get("GITHUB_RUN_ID", "0"),
                    "buildName": os.environ.get("GITHUB_WORKFLOW", "neon-tests"),
                    "buildUrl": f'{os.environ.get("GITHUB_SERVER_URL", "https://github.com")}/{os.environ.get("GITHUB_REPOSITORY", "neon-tests")}/actions/runs/{os.environ.get("GITHUB_RUN_ID", "0")}',
                    "reportUrl": "",
                    "reportName": "Allure report for neon-tests",
                },
                f,
            )


@pytest.fixture(scope="class")
def prepare_account(operator, faucet, web3_client: NeonWeb3Client):
    """Create new account for tests and save operator pre and post balances"""
    with allure.step("Create account for tests"):
        acc = web3_client.eth.account.create()
    with allure.step(
        f"Request {NEON_AIRDROP_AMOUNT} NEON from faucet for {acc.address}"
    ):
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
def bank_account(pytestconfig: Config) -> tp.Optional[Keypair]:
    account = None
    if pytestconfig.environment.use_bank:
        private_key = os.environ.get("BANK_PRIVATE_KEY")
        key = base58.b58decode(private_key)
        account = Keypair.from_secret_key(key)
    yield account


@pytest.fixture(scope="session")
def solana_account(bank_account, pytestconfig: Config, sol_client):
    account = Keypair.generate()
    if pytestconfig.environment.use_bank:
        sol_client.send_sol(
            bank_account, account.public_key, int(0.1 * LAMPORT_PER_SOL)
        )
    else:
        sol_client.request_airdrop(account.public_key, 1 * LAMPORT_PER_SOL)
    yield account
    if pytestconfig.environment.use_bank:
        balance = sol_client.get_balance(account.public_key).value
        sol_client.send_sol(account, bank_account.public_key, balance - 5000)


@pytest.fixture(scope="session")
def erc20_spl(
    web3_client: NeonWeb3Client,
    faucet,
    pytestconfig: Config,
    sol_client,
    solana_account,
):
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(
        web3_client,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client,
        solana_account=solana_account,
        mintable=False,
        evm_loader_id=pytestconfig.environment.evm_loader,
    )
    erc20.token_mint.approve(
        source=erc20.solana_associated_token_acc,
        delegate=sol_client.get_erc_auth_address(
            erc20.account.address,
            erc20.contract.address,
            pytestconfig.environment.evm_loader,
        ),
        owner=erc20.solana_acc.public_key,
        amount=1000000000000000,
    )
    erc20.claim(
        erc20.account, bytes(erc20.solana_associated_token_acc), 100000000000000
    )
    yield erc20


@pytest.fixture(scope="session")
def erc20_spl_mintable(web3_client: NeonWeb3Client, faucet, sol_client, solana_account):
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(
        web3_client,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client,
        solana_account=solana_account,
        mintable=True,
    )
    erc20.mint_tokens(erc20.account, erc20.account.address)
    yield erc20


@pytest.fixture(scope="function")
def new_account(web3_client, faucet):
    new_acc = web3_client.create_account()
    faucet.request_neon(new_acc.address, 100)
    yield new_acc


@pytest.fixture(scope="session")
def neon_mint(pytestconfig: Config):
    neon_mint = PublicKey(pytestconfig.environment.spl_neon_mint)
    return neon_mint
