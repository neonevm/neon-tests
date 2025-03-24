import builtins
import json
import os
import pathlib
import re
import shutil
import sys
from dataclasses import dataclass, field
from typing import Optional, Dict

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item
from _pytest.runner import runtestprotocol
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from spl.token.constants import WRAPPED_SOL_MINT
from web3.middleware import geth_poa_middleware

import allure
from utils import create_allure_environment_opts, setup_logging
from utils.accounts import EthAccounts
from utils.consts import LAMPORT_PER_SOL, EnvName, TEST_GROUPS
from utils.error_log import error_log
from utils.evm_loader import EvmLoader
from utils.faucet import Faucet
from utils.neon_user import NeonUser
from utils.solana_client import SolanaClient
from utils.types import TestGroup, TreasuryPool
from utils.web3client import NeonChainWeb3Client

pytest_plugins = ["ui.plugins.browser"]
COST_REPORT_DIR: pathlib.Path = pathlib.Path()


@dataclass
class EnvironmentConfig:
    name: EnvName
    evm_loader: str
    proxy_url: str
    tracer_url: str
    solana_url: str
    faucet_url: str
    network_ids: Dict[str, int]
    spl_neon_mint: str
    neon_erc20wrapper_address: str
    use_bank: bool
    eth_bank_account: str
    neonpass_url: str = ""
    ws_subscriber_url: str = ""
    account_seed_version: str = "\3"
    neon_core_api_url: Optional[str] = None
    neon_core_api_rpc_url: Optional[str] = None
    sol_mint_id: Pubkey = field(default=WRAPPED_SOL_MINT)


def pytest_addoption(parser: Parser):
    parser.addoption(
        "--network",
        action="store",
        choices=[env.value for env in EnvName],  # noqa
        default="devnet",
        help="Which stand use",
    )
    parser.addoption(
        "--make-report",
        action="store_true",
        default=False,
        help="Store tests result to file",
    )
    parser.addoption(
        "--cost_reports_dir",
        default="",
        type=pathlib.Path,
        help=f"Saves cost reports .json files in {COST_REPORT_DIR}",
    )
    known_args = parser.parse_known_args(args=sys.argv[1:])
    test_group_required = known_args.make_report
    parser.addoption(
        "--test-group",
        choices=TEST_GROUPS,
        required=test_group_required,
        help="Test group",
    )

    parser.addoption("--envs", action="store", default="envs.json", help="Filename with environments")
    parser.addoption(
        "--keep-error-log",
        action="store_true",
        default=False,
        help=f"Don't clear file {error_log.file_path.name}",
    )


def pytest_sessionstart(session: pytest.Session):
    """Hook for clearing the error log used by the Slack notifications utility"""
    keep_error_log = session.config.getoption(name="--keep-error-log", default=False)
    if not keep_error_log:
        error_log.clear()

    if COST_REPORT_DIR != pathlib.Path() and COST_REPORT_DIR.exists() and COST_REPORT_DIR.is_dir():
        shutil.rmtree(COST_REPORT_DIR)


def pytest_runtest_protocol(item: Item, nextitem):
    request: pytest.FixtureRequest = item._request  # noqa
    ihook = item.ihook
    ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    reports = runtestprotocol(item, nextitem=nextitem)
    ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    if item.config.getoption("--make-report"):
        test_group: TestGroup = item.config.getoption("--test-group")
        for report in reports:
            if report.outcome == "failed":
                if report.when == "call":
                    error_log.add_failure(test_group=test_group, test_name=item.nodeid)
                else:
                    error_log.add_error(test_group=test_group, test_name=item.nodeid)
    return True


def pytest_configure(config: Config):
    # redirect print to stderr for xdist-spawned processes because otherwise print statements get lost
    if "PYTEST_XDIST_WORKER" in os.environ:
        original_print = builtins.print
        builtins.print = lambda *args, **kwargs: original_print(*args, file=sys.stderr, **kwargs)

    global COST_REPORT_DIR
    COST_REPORT_DIR = config.getoption("--cost_reports_dir")

    network_name = config.getoption("--network")
    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)
    assert network_name in environments, f"Environment {network_name} doesn't exist in envs.json"
    env = environments[network_name]
    env["name"] = EnvName(network_name)
    if network_name in ["devnet", "tracer_ci"]:
        if "DEVNET_SOLANA_URL" in os.environ and os.environ["DEVNET_SOLANA_URL"]:
            env["solana_url"] = os.environ.get("DEVNET_SOLANA_URL")
        if "PROXY_URL" in os.environ and os.environ["PROXY_URL"]:
            env["proxy_url"] = os.environ.get("PROXY_URL")
        if "DEVNET_FAUCET_URL" in os.environ and os.environ["DEVNET_FAUCET_URL"]:
            env["faucet_url"] = os.environ.get("DEVNET_FAUCET_URL")
    if "use_bank" not in env:
        env["use_bank"] = False
    if "eth_bank_account" not in env:
        env["eth_bank_account"] = ""

    if network_name == "terraform":
        env["solana_url"] = env["solana_url"].replace("<solana_ip>", os.environ.get("SOLANA_IP"))
        env["proxy_url"] = env["proxy_url"].replace("<proxy_ip>", os.environ.get("PROXY_IP"))
        env["faucet_url"] = env["faucet_url"].replace("<proxy_ip>", os.environ.get("PROXY_IP"))
    config.environment = EnvironmentConfig(**env)
    setup_logging()


@pytest.fixture(scope="session")
def env_name(pytestconfig: Config) -> EnvName:
    return pytestconfig.environment.name  # noqa


@pytest.fixture(scope="session")
def operator_keypair() -> Keypair:
    with open("operator-keypair.json", "r") as key:
        secret_key = json.load(key)
        return Keypair.from_bytes(secret_key)


@pytest.fixture(scope="session")
def evm_loader_keypair() -> Keypair:
    with open("evm_loader-keypair.json", "r") as key:
        secret_key = json.load(key)
        return Keypair.from_bytes(secret_key)


@pytest.fixture(scope="session", autouse=True)
def allure_environment(pytestconfig: Config, web3_client_session: NeonChainWeb3Client):
    opts = {}
    network_name = pytestconfig.getoption("--network")
    if network_name != "geth" and network_name != "mainnet" and "neon_evm" not in os.getenv("PYTEST_CURRENT_TEST"):
        opts = {
            "Network": pytestconfig.environment.proxy_url,
            "Proxy.Version": web3_client_session.get_proxy_version()["result"],
            "EVM.Version": web3_client_session.get_evm_version()["result"],
            "NEON_CORE.Version": web3_client_session.get_neon_core_version()["result"],
        }

    yield opts

    allure_dir = pytestconfig.getoption("--alluredir")
    allure_path = pathlib.Path() / allure_dir
    create_allure_environment_opts(opts)
    categories_from = pathlib.Path() / "allure" / "categories.json"
    categories_to = allure_path / "categories.json"
    shutil.copy(categories_from, categories_to)

    if "CI" in os.environ:
        github_server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        github_organization = os.environ.get("GITHUB_REPOSITORY_OWNER")
        github_repository = os.environ.get("GITHUB_REPOSITORY", "neon-tests")
        actions_url = f"{github_server_url}/{github_organization}/{github_repository}/actions"

        with open(allure_path / "executor.json", "w+") as f:
            json.dump(
                {
                    "name": "Github Action",
                    "type": "github",
                    "url": actions_url,
                    "buildOrder": os.environ.get("GITHUB_RUN_ID", "0"),
                    "buildName": os.environ.get("GITHUB_WORKFLOW", "neon-tests"),
                    "buildUrl": f'{actions_url}/runs/{os.environ.get("GITHUB_RUN_ID", "0")}',
                    "reportUrl": "",
                    "reportName": "Allure report for neon-tests",
                },
                f,
            )


@pytest.fixture(scope="session")
def web3_client_session(
    environment: EnvironmentConfig,
    env_name: EnvName,
) -> NeonChainWeb3Client:
    client = NeonChainWeb3Client(
        environment.proxy_url,
        tracer_url=environment.tracer_url,
    )
    if env_name is EnvName.GETH:
        client._web3.middleware_onion.inject(geth_poa_middleware, layer=0)  # noqa
    return client


@pytest.fixture(scope="session")
def sol_client_session(environment: EnvironmentConfig) -> SolanaClient:
    return SolanaClient(environment.solana_url, environment.account_seed_version)


@pytest.fixture(scope="session")
def faucet(environment: EnvironmentConfig, web3_client_session: NeonChainWeb3Client) -> Faucet:
    return Faucet(environment.faucet_url, web3_client_session)


@pytest.fixture(scope="session")
def accounts_session(pytestconfig: Config, web3_client_session, faucet, eth_bank_account):
    accounts = EthAccounts(web3_client_session, faucet, eth_bank_account)
    yield accounts
    if pytestconfig.getoption("--network") == "mainnet":
        if len(accounts.accounts_collector) > 0:
            for item in accounts.accounts_collector:
                with allure.step(f"Restoring eth account balance from {item.key.hex()} account"):
                    web3_client_session.send_all_neons(item, eth_bank_account)
    accounts_session._accounts = []


@pytest.fixture(scope="function")
def neon_user(evm_loader: EvmLoader, bank_account, environment: EnvironmentConfig) -> NeonUser:
    user = NeonUser(environment.evm_loader, bank_account)
    lamports = 2 * LAMPORT_PER_SOL

    if environment.use_bank:
        balance = evm_loader.get_solana_balance(user.solana_account.pubkey())
        if balance < lamports:
            evm_loader.send_sol(bank_account, user.solana_account.pubkey(), lamports)
    else:
        evm_loader.request_airdrop(
            pubkey=user.solana_account.pubkey(),
            lamports=lamports,
            commitment=Confirmed,
        )
    return user


@pytest.fixture(scope="function")
def neon_user_no_sols(pytestconfig, bank_account, faucet, environment) -> NeonUser:
    user = NeonUser(environment.evm_loader, bank_account)
    return user


@pytest.fixture(scope="session")
def treasury_pool(evm_loader: EvmLoader, pytestconfig, index_of_process) -> TreasuryPool:
    index = index_of_process
    evm_loader.create_treasury_pool_address(index)
    if pytestconfig.getoption("--network") == "mainnet":
        address = Pubkey.from_string(os.environ.get("MAINNET_TREASURY_POOL_ADDRESS"))
    else:
        address = evm_loader.create_treasury_pool_address(index)
    index_buf = index.to_bytes(4, "little")
    balance = evm_loader.get_solana_balance(address)
    if pytestconfig.getoption("--network") not in ["mainnet", "devnet"]:
        if balance < 5 * LAMPORT_PER_SOL:
            evm_loader.request_airdrop(address, 5 * LAMPORT_PER_SOL, commitment=Confirmed)
    return TreasuryPool(index, address, index_buf)


@pytest.fixture(scope="session")
def treasury_pool_new(evm_loader, pytestconfig) -> TreasuryPool:
    index = 3
    address = evm_loader.create_treasury_pool_address(index)
    index_buf = index.to_bytes(4, "little")
    if pytestconfig.getoption("--network") not in ["mainnet", "devnet"]:
        evm_loader.request_airdrop(address, 10000 * 10**9, commitment=Confirmed)
    return TreasuryPool(index, address, index_buf)


@pytest.fixture(scope="session")
def index_of_process(worker_id):
    if worker_id in ("master", "gw1"):
        return 1
    match = re.search(r"gw(\d+)", worker_id)
    return int(match.group(1)) if match else None
