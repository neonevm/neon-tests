import builtins
import os
import json
import shutil
import pathlib
import sys
from dataclasses import dataclass

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item
from _pytest.runner import runtestprotocol
from solders.keypair import Keypair
from web3.middleware import geth_poa_middleware

from clickfile import TEST_GROUPS, EnvName
from utils.types import TestGroup
from utils.error_log import error_log
from utils import create_allure_environment_opts, setup_logging
from utils.faucet import Faucet
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client
from utils.solana_client import SolanaClient


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
    network_ids: dict
    spl_neon_mint: str
    neon_erc20wrapper_address: str
    use_bank: bool
    eth_bank_account: str
    neonpass_url: str = ""
    ws_subscriber_url: str = ""
    account_seed_version: str = "\3"


def pytest_addoption(parser: Parser):
    parser.addoption(
        "--network",
        action="store",
        choices=[env.value for env in EnvName],  # noqa
        default="night-stand",
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

    solana_url_env_vars = ["SOLANA_URL", "DEVNET_INTERNAL_RPC", "MAINNET_INTERNAL_RPC"]
    network_name = config.getoption("--network")
    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)
    assert network_name in environments, f"Environment {network_name} doesn't exist in envs.json"
    env = environments[network_name]
    env["name"] = EnvName(network_name)
    if network_name in ["devnet", "tracer_ci"]:
        for solana_env_var in solana_url_env_vars:
            if solana_env_var in os.environ and os.environ[solana_env_var]:
                env["solana_url"] = os.environ.get(solana_env_var)
                break
        if "PROXY_URL" in os.environ and os.environ["PROXY_URL"]:
            env["proxy_url"] = os.environ.get("PROXY_URL")
        if "DEVNET_FAUCET_URL" in os.environ and os.environ["DEVNET_FAUCET_URL"]:
            env["faucet_url"] = os.environ.get("DEVNET_FAUCET_URL")
    if "use_bank" not in env:
        env["use_bank"] = False
    if "eth_bank_account" not in env:
        env["eth_bank_account"] = ""

    # Set envs for integration/tests/neon_evm project
    if "SOLANA_URL" not in os.environ or not os.environ["SOLANA_URL"]:
        os.environ["SOLANA_URL"] = env["solana_url"]
    if "EVM_LOADER" not in os.environ or not os.environ["EVM_LOADER"]:
        os.environ["EVM_LOADER"] = env["evm_loader"]
    if "NEON_TOKEN_MINT" not in os.environ or not os.environ["NEON_TOKEN_MINT"]:
        os.environ["NEON_TOKEN_MINT"] = env["spl_neon_mint"]
    if "CHAIN_ID" not in os.environ or not os.environ["CHAIN_ID"]:
        os.environ["CHAIN_ID"] = str(env["network_ids"]["neon"])

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
def operator_keypair():
    with open("operator-keypair.json", "r") as key:
        secret_key = json.load(key)
        return Keypair.from_bytes(secret_key)


@pytest.fixture(scope="session")
def evm_loader_keypair():
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
        pytestconfig: Config,
        env_name: EnvName,
) -> NeonChainWeb3Client:
    client = NeonChainWeb3Client(
        pytestconfig.environment.proxy_url,
        tracer_url=pytestconfig.environment.tracer_url,
    )
    if env_name is EnvName.GETH:
        client._web3.middleware_onion.inject(geth_poa_middleware, layer=0)  # noqa
    return client


@pytest.fixture(scope="session")
def sol_client_session(pytestconfig: Config) -> SolanaClient:
    client = SolanaClient(
        pytestconfig.environment.solana_url,
        pytestconfig.environment.account_seed_version,
    )
    return client


@pytest.fixture(scope="session", autouse=True)
def faucet(pytestconfig: Config, web3_client_session) -> Faucet:
    return Faucet(pytestconfig.environment.faucet_url, web3_client_session)


@pytest.fixture(scope="session")
def accounts_session(pytestconfig: Config, web3_client_session, faucet, eth_bank_account):
    accounts = EthAccounts(web3_client_session, faucet, eth_bank_account)
    return accounts
