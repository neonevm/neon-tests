#!/usr/bin/env python3
import enum
import functools
import glob
import json
import time
from collections import defaultdict
from multiprocessing.dummy import Pool

import os
import re
import shutil
import subprocess
import sys
import typing as tp
from pathlib import Path
from urllib.parse import urlparse

import pytest

from deploy.test_results_db.db_handler import PostgresTestResultsHandler
from deploy.test_results_db.test_results_handler import TestResultsHandler
from utils.error_log import error_log
from utils.slack_notification import SlackNotification
from utils.types import TestGroup, RepoType

try:
    import click
    import requests
    import tabulate
    import yaml
except ImportError:
    print("Please install dependencies: pip3 install -r deploy/requirements/click.txt")
    sys.exit(1)

try:
    from deploy.cli.github_api_client import GithubClient
    from deploy.cli.network_manager import NetworkManager
    from deploy.cli import dapps as dapps_cli

    from utils import create_allure_environment_opts, time_measure
    from deploy.cli import infrastructure
    from utils import web3client
    from utils import cloud
    from utils.operator import Operator
    from utils.web3client import NeonChainWeb3Client
    from utils.prices import get_sol_price
    from utils.helpers import wait_condition
    from utils.apiclient import JsonRPCSession
except ImportError:
    print("Please run ./clickfile.py requirements to install all requirements")

ALLURE_REPORT_URL = "allure_report.url"

ERR_MESSAGES = {
    "run": "Unsuccessful tests executing",
    "requirements": "Unsuccessful requirements installation",
}

SRC_ALLURE_CATEGORIES = Path("./allure/categories.json")

DST_ALLURE_CATEGORIES = Path("./allure-results/categories.json")

DST_ALLURE_ENVIRONMENT = Path("./allure-results/environment.properties")

BASE_EXTENSIONS_TPL_DATA = "ui/extensions/data"

EXTENSIONS_PATH = "ui/extensions/chrome/plugins"
EXTENSIONS_USER_DATA_PATH = "ui/extensions/chrome"

HOME_DIR = Path(__file__).absolute().parent

OZ_BALANCES = "./compatibility/results/oz_balance.json"
DOCKER_HUB_ORG_NAME = os.environ.get("DOCKER_HUB_ORG_NAME")
NEON_EVM_GITHUB_URL = f"https://api.github.com/repos/{DOCKER_HUB_ORG_NAME}/neon-evm"
HOODIES_CHAINLINK_GITHUB_URL = "https://github.com/hoodieshq/chainlink-neon"
PROXY_GITHUB_URL = f"https://api.github.com/repos/{DOCKER_HUB_ORG_NAME}/neon-proxy.py"
FAUCET_GITHUB_URL = f"https://api.github.com/repos/{DOCKER_HUB_ORG_NAME}/neon-faucet"
EXTERNAL_CONTRACT_PATH = Path.cwd() / "contracts" / "external"
VERSION_BRANCH_TEMPLATE = r"[vt]{1}\d{1,2}\.\d{1,2}\.x.*"
GITHUB_TAG_PATTERN = re.compile(r'^[vt]\d{1,2}\.\d{1,2}\.\d{1,2}$')

TEST_GROUPS: tp.Tuple[TestGroup, ...] = tp.get_args(TestGroup)

network_manager = NetworkManager()


class EnvName(str, enum.Enum):
    NIGHT_STAND = "night-stand"
    RELEASE_STAND = "release-stand"
    MAINNET = "mainnet"
    DEVNET = "devnet"
    TESTNET = "testnet"
    LOCAL = "local"
    TERRAFORM = "terraform"
    GETH = "geth"
    TRACER_CI = "tracer_ci"
    CUSTOM = "custom"
    DOCKER_NET = "docker_net"


def green(s):
    return click.style(s, fg="green")


def yellow(s):
    return click.style(s, fg="yellow")


def red(s):
    return click.style(s, fg="red")


def catch_traceback(func: tp.Callable) -> tp.Callable:
    """Catch traceback to file"""
    def add_error_log_comment(func_name, exc: BaseException):
        err_msg = ERR_MESSAGES.get(func_name) or f"{exc.__class__.__name__}({exc})"
        error_log.add_comment(text=f"{func_name}: {err_msg}")

    @functools.wraps(func)
    def wrap(*args, **kwargs) -> tp.Any:
        error: tp.Optional[BaseException] = None

        try:
            result = func(*args, **kwargs)
        except SystemExit as e:
            exit_code = e.args[0]
            if exit_code != 0:
                error = e
        except BaseException as e:
            error = e
        else:
            return result

        finally:
            if error:
                if not error_log.has_logs():
                    add_error_log_comment(func.__name__, error)
                raise error

    return wrap


def check_profitability(func: tp.Callable) -> tp.Callable:
    """Calculate profitability of OZ cases"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> None:
        network = network_manager.get_network_object(args[0])
        w3client = web3client.NeonChainWeb3Client(network["proxy_url"])

        def get_tokens_balances(operator: Operator) -> tp.Dict:
            """Return tokens balances"""
            return dict(
                neon=w3client.to_main_currency(operator.get_token_balance()),
                sol=operator.get_solana_balance() / 1_000_000_000,
            )

        def float_2_str(d):
            return dict(map(lambda i: (i[0], str(i[1])), d.items()))

        if os.environ.get("OZ_BALANCES_REPORT_FLAG") is not None:
            op = Operator(
                network["proxy_url"],
                network["solana_url"],
                network["spl_neon_mint"],
                web3_client=w3client,
                evm_loader=network["evm_loader"],
            )
            pre = get_tokens_balances(op)
            try:
                func(*args, **kwargs)
            except subprocess.CalledProcessError:
                pass
            after = get_tokens_balances(op)
            profitability = dict(
                neon=round(float(after["neon"] - pre["neon"]) * 0.25, 2),
                sol=round((float(pre["sol"] - after["sol"])) * get_sol_price(), 2),
            )
            path = Path(OZ_BALANCES)
            path.absolute().parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as fd:
                balances = dict(
                    pre=float_2_str(pre),
                    after=float_2_str(after),
                    profitability=float_2_str(profitability),
                )
                json.dump(balances, fp=fd, indent=4, sort_keys=True)
        else:
            func(*args, **kwargs)

    return wrapper


@check_profitability
def run_openzeppelin_tests(network, jobs=8, amount=20000, users=8):
    print(f"Running OpenZeppelin tests in {jobs} jobs on {network}")
    cwd = (Path().parent / "compatibility/openzeppelin-contracts").absolute()
    if not list(cwd.glob("*")):
        subprocess.check_call("git submodule init && git submodule update", shell=True, cwd=cwd)
        subprocess.check_call("npm ci", shell=True, cwd=cwd)
    log_dir = cwd.parent / "results"
    log_dir.mkdir(parents=True, exist_ok=True)

    tests = list(Path(f"{cwd}/test").rglob("*.test.js"))
    priority_names = [
        "test/token/ERC721/ERC721.test.js",
        "test/token/ERC721/ERC721Enumerable.test.js",
        "test/token/ERC721/extensions/ERC721Wrapper.test.js",
    ]
    priority_tests = []
    other_tests = []
    for test in tests:
        test = str(test)
        if any(test.endswith(priority_name) for priority_name in priority_names):
            priority_tests.append(test)
        else:
            other_tests.append(test)

    prioritised_tests = priority_tests + other_tests

    keys_env = [infrastructure.prepare_accounts(network, users, amount) for i in range(jobs)]

    def run_oz_file(file_name):
        print(f"Run {file_name}")
        keys = keys_env.pop(0)
        env = os.environ.copy()
        env["PRIVATE_KEYS"] = ",".join(keys)
        env["NETWORK_ID"] = str(network_manager.get_network_param(network, "network_ids.neon"))
        env["PROXY_URL"] = network_manager.get_network_param(network, "proxy_url")

        start_time = time.time()
        out = subprocess.run(
            f"npx hardhat test {file_name}",
            shell=True,
            cwd=cwd,
            capture_output=True,
            env=env,
        )
        end_time = time.time()
        stdout = out.stdout.decode()
        stderr = out.stderr.decode()
        time_info = time_measure(start_time=start_time, end_time=end_time, job_name=file_name)
        print(f"Test {file_name} finished with code {out.returncode}")
        print(stdout)
        print(stderr)
        print(time_info)

        keys_env.append(keys)
        log_dirs = cwd.parent / "results" / file_name.replace(".", "_").replace("/", "_")
        log_dirs.mkdir(parents=True, exist_ok=True)
        with open(log_dirs / "stdout.log", "w") as f:
            f.write(stdout)
        with open(log_dirs / "stderr.log", "w") as f:
            f.write(stderr)
        with open(log_dirs / "time.log", "w") as f:
            f.write(time_info)

    print("Run tests in parallel")
    pool = Pool(jobs)
    pool.map(run_oz_file, prioritised_tests, chunksize=1)
    pool.close()
    pool.join()

    with open(log_dir / "time.log", "w") as merged_log:
        for sub_dir in log_dir.iterdir():
            if sub_dir.is_dir():
                time_log_path = sub_dir / "time.log"
                if time_log_path.exists():
                    with open(time_log_path, "r") as time_log:
                        contents = time_log.read()
                        merged_log.write(contents + "\n")

    # Add allure environment
    settings = network_manager.get_network_object(network)
    web3_client = web3client.NeonChainWeb3Client(settings["proxy_url"])
    opts = {
        "Proxy.Version": web3_client.get_proxy_version()["result"],
        "EVM.Version": web3_client.get_evm_version()["result"],
        "CLI.Version": web3_client.get_cli_version()["result"],
    }
    create_allure_environment_opts(opts, DST_ALLURE_ENVIRONMENT)
    # Add epic name for allure result files
    openzeppelin_reports = Path("./allure-results")
    res_file_list = [str(res_file) for res_file in openzeppelin_reports.glob("*-result.json")]
    shutil.copyfile(log_dir / "time.log", openzeppelin_reports / "time_consolidated.log")
    print("Fix allure results: {}".format(len(res_file_list)))

    for res_file in res_file_list:
        with open(res_file, "r+") as f:
            report = json.load(f)
        report["labels"].append({"name": "epic", "value": "OpenZeppelin contracts"})
        with open(res_file, "w+") as f:
            json.dump(report, f)


def parse_openzeppelin_results():
    test_report = {"passing": 0, "pending": 0, "failing": 0}

    skipped_files = []

    stdout_files = glob.glob("./compatibility/results/**/stdout.log", recursive=True)
    print("`stdout` files found: {}. Processing ...\n".format(len(stdout_files)))

    for stdout in stdout_files:
        with open(stdout, "r+", encoding="utf8") as f:
            rep = f.read()
            result = re.findall(r"(\d+) (passing|pending|failing)", rep)
            if not result:
                skipped_files.append(stdout)
            for count in result:
                test_report[count[1]] += int(count[0])
    return test_report, skipped_files


def print_test_suite_results(test_report: tp.Dict[str, int], skipped_files: tp.List[str]):
    print("Summarize result:\n")
    for state in test_report:
        print("    {} - {}".format(state.capitalize(), test_report[state]))
    print("\nTotal tests - {:d}\n".format(sum(test_report.values())))

    print("Test files without test result - {}:\n".format(len(skipped_files)))

    for f in skipped_files:
        test_file_name = f.split("/", 3)[3].rsplit("/", 1)[0].replace("_", "")
        print("    {}".format(test_file_name))


def print_oz_balances():
    """Print token balances after oz tests"""
    path = Path(OZ_BALANCES)
    if not path.exists():
        print(red(f"OZ balances report not found on `{path.resolve()}` !"))
        return

    with open(path, "r") as fd:
        balances = json.load(fd)
    report = tabulate.tabulate(
        [
            [
                "NEON",
                balances["pre"]["neon"],
                balances["after"]["neon"],
                balances["profitability"]["neon"],
            ],
            [
                "SOL",
                balances["pre"]["sol"],
                balances["after"]["sol"],
                balances["profitability"]["sol"],
            ],
        ],
        headers=["token", "on start balance", "os stop balance", "P/L (USD)"],
        tablefmt="fancy_outline",
        numalign="right",
        floatfmt=".2f",
    )
    print(green("\nOZ tests suite profitability:"))
    print(yellow(report))


def wait_for_tracer_service(network: str):
    settings = network_manager.get_network_object(network)
    web3_client = web3client.NeonChainWeb3Client(proxy_url=settings["proxy_url"])
    tracer_api = JsonRPCSession(settings["tracer_url"])

    block = web3_client.get_block_number()

    wait_condition(
        lambda: (tracer_api.send_rpc(method="get_neon_revision", params=block)["result"]["neon_revision"]) is not None,
        timeout_sec=180,
    )

    return True


def generate_allure_environment(network_name: str):
    network = network_manager.get_network_object(network_name)
    env = os.environ.copy()

    env["NETWORK_ID"] = str(network["network_ids"]["neon"])
    env["PROXY_URL"] = network["proxy_url"]
    return env


def install_python_requirements():
    command = (
        "uv pip install --upgrade "
        "-r deploy/requirements/click.txt "
        "-r deploy/requirements/prod.txt  "
        "-r deploy/requirements/devel.txt"
    )
    subprocess.check_call(command, shell=True)


def install_ui_requirements():
    click.echo(green("Install python requirements for Playwright"))
    command = "uv pip install --upgrade -r deploy/requirements/ui.txt"
    subprocess.check_call(command, shell=True)
    # On Linux Playwright require `xclip` to work.
    if sys.platform in ["linux", "linux2"]:
        try:
            command = "apt update && apt install xclip"
            subprocess.check_call(command, shell=True)
        except Exception:
            click.echo(
                red(
                    f"{10 * '!'} Warning: Linux requires `xclip` to work. "
                    f"Install with your package manager, e.g. `sudo apt install xclip` {10 * '!'}"
                ),
                color=True,
            )
    # install ui test deps,
    # download the Playwright package and install browser binaries for Chromium, Firefox and WebKit.
    click.echo(green("Install browser binaries for Chromium."))
    subprocess.check_call("playwright install chromium", shell=True)


@click.group()
def cli():
    pass


@cli.command(help="Install neon-tests dependencies")
@click.option(
    "-d",
    "--dep",
    default="devel",
    type=click.Choice(["devel", "python", "ui", "all"]),
    help="Which deps install",
)
@catch_traceback
def requirements(dep):
    if dep in ["devel", "python"]:
        install_python_requirements()
    if dep == "ui":
        install_ui_requirements()
    if dep == "all":
        install_python_requirements()
        install_ui_requirements()


def is_branch_exist(endpoint, branch):
    if branch:
        response = requests.get(f"{endpoint}/branches/{branch}")
        if response.status_code == 200:
            click.echo(f"The branch {branch} exist in the {endpoint} repository")
            return True
    else:
        return False


def get_evm_pinned_version(branch):
    click.echo(f"Get pinned version for proxy branch {branch}")
    resp = requests.get(f"{PROXY_GITHUB_URL}/contents/.github/workflows/pipeline.yml?ref={branch}")

    if resp.status_code != 200:
        click.echo(f"Can't get pipeline file for {PROXY_GITHUB_URL}: {resp.text}")
        raise click.ClickException(f"Can't get pipeline file for branch {branch}")
    info = resp.json()
    pipeline_file = yaml.safe_load(requests.get(info["download_url"]).text)
    tag = pipeline_file["env"]["DEFAULT_NEON_EVM_TAG"]
    if tag == "latest":
        return "develop"
    if re.match(r"[vt]{1}\d{1,2}\.\d{1,2}.*", tag) is not None:
        tag = re.sub(r"\.\d+$", ".x", tag)
    return tag


def update_contracts_from_git(git_url: str, local_dir_name: str, branch="develop", update_npm: bool = True):
    download_path = EXTERNAL_CONTRACT_PATH / local_dir_name
    click.echo(f"Downloading contracts from {git_url} {branch}")
    if download_path.exists():
        shutil.rmtree(download_path)
    commands = f"""
        git clone --branch {branch} {git_url} {download_path}
    """

    if update_npm:
        commands += f"\n npm ci --prefix {download_path}"

    subprocess.check_call(commands, shell=True)
    click.echo(f"Contracts downloaded from {git_url} {branch} to {EXTERNAL_CONTRACT_PATH / local_dir_name}")


def download_evm_contracts(branch):
    if is_branch_exist(NEON_EVM_GITHUB_URL, branch) and branch != "develop":
        neon_evm_branch = branch
    else:
        neon_evm_branch = get_evm_pinned_version("develop")
    click.echo(f"Contracts would be downloaded from {neon_evm_branch} neon-evm branch")
    Path(EXTERNAL_CONTRACT_PATH / "neon-evm").mkdir(parents=True, exist_ok=True)

    click.echo(f"Check contract availability in neon-evm repo")
    response = requests.get(f"{NEON_EVM_GITHUB_URL}/contents/solidity?ref={neon_evm_branch}")
    if response.status_code != 200:
        click.echo(f"Repository doesn't has solidity directory, check old structure")
        response = requests.get(f"{NEON_EVM_GITHUB_URL}/contents/evm_loader/solidity?ref={neon_evm_branch}")
        if response.status_code != 200:
            raise click.ClickException(f"Can't get contracts from neon-evm repo: {response.text}")

    for item in response.json():
        click.echo(f"Downloading {item['name']}")
        r = requests.get(item["download_url"])
        if r.status_code == 200:
            with open(EXTERNAL_CONTRACT_PATH / "neon-evm" / item["name"], "wb") as f:
                f.write(r.content)
            click.echo(f" {item['name']} downloaded")
        else:
            raise click.ClickException(f"The contract {item['name']} is not downloaded. Error: {r.text}")


@cli.command(help="Download test contracts from neon-evm repo")
@click.option(
    "--branch",
    default="develop",
    help="neon_evm branch name. " "If branch doesn't exist, develop branch will be used",
)
def update_contracts(branch):
    download_evm_contracts(branch)
    update_contracts_from_git(HOODIES_CHAINLINK_GITHUB_URL, "hoodies_chainlink", "main")

    update_contracts_from_git(
        f"https://github.com/{DOCKER_HUB_ORG_NAME}/neon-contracts.git", "neon-contracts", "main", update_npm=False
    )
    subprocess.check_call(f'npm ci --prefix {EXTERNAL_CONTRACT_PATH / "neon-contracts" / "ERC20ForSPL"}', shell=True)


@cli.command(help="Run any type of tests")
@click.option("-n", "--network", type=click.Choice(EnvName),
              help="In which stand run tests")
@click.option("-j", "--jobs", default=8, help="Number of parallel jobs (for openzeppelin)")
@click.option("-p", "--numprocesses", help="Number of parallel jobs for basic tests")
@click.option("-a", "--amount", default=20000, help="Requested amount from faucet")
@click.option("-u", "--users", default=8, help="Accounts numbers used in OZ tests")
@click.option("-c", "--case", default="", type=str, help="Specific test case name pattern to run")
@click.option("--marker", help="Run tests by mark")
@click.option(
    "--ui-item",
    default="all",
    type=click.Choice(["faucet", "neonpass", "all"]),
    help="Which UI test run",
)
@click.option(
    "--keep-error-log",
    is_flag=True,
    default=False,
    help=f"Don't clear {error_log.file_path.name} before run"
)
@click.argument(
    "name",
    required=True,
    type=click.Choice(TEST_GROUPS),
)
@catch_traceback
def run(
        name: TestGroup,
        jobs,
        numprocesses,
        ui_item,
        amount,
        users,
        network: EnvName,
        case,
        keep_error_log: bool,
        marker: str,
):
    if not network and name == "ui":
        network = "devnet"
    if DST_ALLURE_CATEGORIES.parent.exists():
        shutil.rmtree(DST_ALLURE_CATEGORIES.parent, ignore_errors=True)
    DST_ALLURE_CATEGORIES.parent.mkdir()
    if name == "economy":
        command = "py.test integration/tests/economy/test_economics.py"
    elif name == "basic":
        if network == "mainnet":
            command = "py.test integration/tests/basic -m mainnet"
        else:
            command = "py.test integration/tests/basic"
        if numprocesses:
            command = f"{command} --numprocesses {numprocesses} --dist loadgroup"
    elif name == "tracer":
        command = "py.test -n 5 integration/tests/tracer"
    elif name == "services":
        command = "py.test integration/tests/services"
        if numprocesses:
            command = f"{command} --numprocesses {numprocesses}"
    elif name == "compiler_compatibility":
        command = "py.test integration/tests/compiler_compatibility"
        if numprocesses:
            command = f"{command} --numprocesses {numprocesses} --dist loadscope"
    elif name == "evm":
        command = "py.test integration/tests/neon_evm"
        if numprocesses:
            command = f"{command} --numprocesses {numprocesses}"
    elif name == "oz":
        if not keep_error_log:
            error_log.clear()
        run_openzeppelin_tests(network, jobs=int(jobs), amount=int(amount), users=int(users))
        return
    elif name == "ui":
        if not os.environ.get("CHROME_EXT_PASSWORD"):
            raise click.ClickException(
                red("Please set the `CHROME_EXT_PASSWORD` environment variable (password for wallets).")
            )
        command = "py.test ui/tests"
        if ui_item != "all":
            command = command + f"/test_{ui_item}.py"
    else:
        raise click.ClickException("Unknown test name")

    if name == "tracer":
        if network != "geth":
            assert wait_for_tracer_service(network)

    if case != "":
        command += " -vk {}".format(case)
    if marker:
        command += f" -m {marker}"

    command += f" -s --network={network} --make-report --test-group {name}"
    if keep_error_log:
        command += " --keep-error-log"
    args = command.split()[1:]
    exit_code = int(pytest.main(args=args))
    if name != "ui":
        shutil.copyfile(SRC_ALLURE_CATEGORIES, DST_ALLURE_CATEGORIES)

    sys.exit(exit_code)


@cli.command(
    help="OZ actions:\n"
         "report - summarize openzeppelin tests results\n"
         "analyze - analyze openzeppelin tests results"
)
@click.argument(
    "name",
    required=True,
    type=click.Choice(["report", "analyze"]),
)
def oz(name):
    if name == "report":
        test_report, skipped_files = parse_openzeppelin_results()
        print_test_suite_results(test_report, skipped_files)
        print_oz_balances()
        return
    elif name == "analyze":
        analyze_openzeppelin_results()
        return


@catch_traceback
def analyze_openzeppelin_results():
    test_report, skipped_files = parse_openzeppelin_results()
    failed_tests_count = test_report["failing"]
    dummy_failed_test_names = ["" for _ in range(failed_tests_count)]

    with open("./compatibility/openzeppelin-contracts/package.json") as f:
        version = json.load(f)["version"]
        print(f"OpenZeppelin version: {version}")

    if version.startswith("3") or version.startswith("2"):
        if version.startswith("3"):
            threshold = 1350
        else:
            threshold = 2293
        print(f"Threshold: {threshold}")
        if test_report["passing"] < threshold:
            error_log.add_failures(test_group="oz", test_names=dummy_failed_test_names)
            raise click.ClickException(
                f"OpenZeppelin {version} tests failed. \n" f"Passed: {test_report['passing']}, expected: {threshold}"
            )
        else:
            print("OpenZeppelin tests passed")
    else:
        if test_report["failing"] > 0 or test_report["passing"] == 0:
            error_log.add_failures(test_group="oz", test_names=dummy_failed_test_names)
            raise click.ClickException(
                f"OpenZeppelin {version} tests failed. \n"
                f"Failed: {test_report['failing']}, passed: {test_report['passing']}"
            )
        else:
            print("OpenZeppelin tests passed")


# Base locust options
locust_credentials = click.option(
    "-c",
    "--credentials",
    type=str,
    help="Relative path to credentials. Default repo root/envs.json",
    show_default=True,
)

locust_host = click.option(
    "-h",
    "--host",
    default="night-stand",
    type=str,
    help="In which stand run tests.",
    show_default=True,
)

locust_users = click.option(
    "-u",
    "--users",
    default=50,
    type=int,
    help="Peak number of concurrent Locust users.",
    show_default=True,
)

locust_rate = click.option(
    "-r",
    "--spawn-rate",
    default=1,
    type=int,
    help="Rate to spawn users at (users per second)",
    show_default=True,
)

locust_run_time = click.option(
    "-t",
    "--run-time",
    type=int,
    help="Stop after the specified amount of time, e.g. (300s, 20m, 3h, 1h30m, etc.). "
         "Only used together without Locust Web UI. [default: always run]",
)

locust_tags = click.option(
    "-T",
    "--tag",
    type=str,
    multiple=True,
    help="tag to include in the test, so only tasks " "with any matching tags will be executed",
)

locust_headless = click.option(
    "--web-ui/--headless",
    " /-w",
    default=True,
    help="Enable the web interface. " "If UI is enabled, go to http://0.0.0.0:8089/ [default: `Web UI is enabled`]",
)


@cli.group()
@click.pass_context
def locust(ctx):
    """Commands for load test manipulation."""


@locust.command("run", help="Run `neon` pipeline performance test")
@locust_credentials
@locust_host
@locust_users
@locust_rate
@locust_run_time
@locust_tags
@locust_headless
@click.option(
    "-f",
    "--locustfile",
    type=click.Choice(["proxy", "synthetic", "tracerapi"]),
    default="proxy",
    help="Load test type. It's sub-folder name to import.",
    show_default=True,
)
@click.option(
    "--neon-rpc",
    type=str,
    help="NEON RPC entry point.",
    show_default=True,
)
def run(credentials, host, users, spawn_rate, run_time, tag, web_ui, locustfile, neon_rpc):
    """Run `Neon` pipeline performance test

    path it's sub-folder and file name  `loadtesting/locustfile.py`.
    """
    base_path = Path(__file__).parent
    path = base_path / f"loadtesting/{locustfile}/locustfile.py"
    if not (path.exists() and path.is_file()):
        raise FileNotFoundError(f"path doe's not exists. {path.resolve()}")
    command = f"locust -f {path.as_posix()} --host={host} --users={users} --spawn-rate={spawn_rate}"
    if credentials:
        command += f" --credentials={credentials}"
    elif locustfile == "tracerapi":
        command += f" --credentials={base_path.absolute()}/loadtesting/tracerapi/envs.json"
    if run_time:
        command += f" --run-time={run_time}"
    if neon_rpc and locustfile == "tracerapi":
        command += f" --neon-rpc={neon_rpc}"
    if tag:
        command += f" --tags {' '.join(tag)}"
    if not web_ui:
        command += f" --headless"

    cmd = subprocess.run(command, shell=True)

    if cmd.returncode != 0:
        sys.exit(cmd.returncode)


@locust.command("prepare", help="Run preparation stage for `tracer api` performance test")
@locust_credentials
@locust_host
@locust_users
@locust_rate
@locust_run_time
@locust_tags
def prepare(credentials, host, users, spawn_rate, run_time, tag):
    """Run `Preparation stage` for trace api performance test"""
    base_path = Path(__file__).parent
    path = base_path / "loadtesting/tracerapi/prepare_data/locustfile.py"
    if not (path.exists() and path.is_file()):
        raise FileNotFoundError(f"path doe's not exists. {path.resolve()}")
    command = f"locust -f {path.absolute()} --host={host} --users={users} --spawn-rate={spawn_rate} --headless"
    if credentials:
        command += f" --credentials={credentials}"
    else:
        command += f" --credentials={base_path.absolute()}/envs.json"
    if run_time:
        command += f" --run-time={run_time}"
    else:
        command += f" --run-time=120"
    if tag:
        command += f" --tags {' '.join(tag)}"
    else:
        command += f" --tags prepare"

    cmd = subprocess.run(command, shell=True)

    if cmd.returncode != 0:
        sys.exit(cmd.returncode)


@cli.group("allure")
@click.pass_context
def allure_cli(ctx):
    """Commands for load test manipulation."""


@allure_cli.command("get-history", help="Download allure history")
@click.argument("name", type=click.STRING)
@click.option("-n", "--network", default="night-stand", type=str, help="In which stand run tests")
@click.option(
    "-d",
    "--destination",
    default="./allure-results",
    type=click.Path(file_okay=False, dir_okay=True),
)
def get_allure_history(name: str, network: str, destination: str = "./allure-results"):
    branch = os.environ.get("GITHUB_REF_NAME")
    path = Path(name) / network / branch

    runs = []
    previous_runs = cloud.client.list_objects_v2(
        Bucket=cloud.NEON_TESTS_BUCKET_NAME, Prefix=f"{path}/", Delimiter="/"
    ).get("CommonPrefixes", [])
    for run in previous_runs:
        run_id = re.findall(r"(\d+)", run["Prefix"])
        if len(run_id) > 0:
            runs.append(int(run_id[0]))
    if len(runs) > 0:
        print(f"Downloading allure history from build: {max(runs)}")
        cloud.download(path / str(max(runs)) / "history", Path(destination) / "history")


@allure_cli.command("upload-report", help="Upload allure history")
@click.argument("name", type=click.Choice(TEST_GROUPS))
@click.option("-n", "--network", default=EnvName.NIGHT_STAND, type=EnvName, help="In which stand run tests")
@click.option(
    "-s",
    "--source",
    default="./allure-report",
    type=click.Path(file_okay=False, dir_okay=True),
)
def upload_allure_report(name: TestGroup, network: EnvName, source: str = "./allure-report"):
    branch = os.environ.get("GITHUB_REF_NAME")
    build_id = os.environ.get("GITHUB_RUN_NUMBER")
    path = Path(name) / network.value / branch
    cloud.upload(source, path / build_id)
    report_url = f"http://neon-test-allure.s3-website.eu-central-1.amazonaws.com/{path / build_id}"

    with open(ALLURE_REPORT_URL, "w") as f:
        f.write(report_url)

    with open("/tmp/index.html", "w") as f:
        f.write(
            f"""<!DOCTYPE html><meta charset="utf-8"><meta http-equiv="refresh" content="0; URL={report_url}">
        <meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">
        """
        )

    cloud.upload("/tmp/index.html", path)
    print(f"Allure report link: {report_url}")

    with open("allure_report_info", "w") as f:
        f.write(f"🔗 Allure [report]({report_url})\n")


@allure_cli.command("generate", help="Generate allure history")
def generate_allure_report():
    cmd = subprocess.run("allure generate", shell=True)
    if cmd.returncode != 0:
        sys.exit(cmd.returncode)


@cli.command(help="Send notification to slack")
@click.option("-u", "--url", help="slack app endpoint url.")
@click.option("-b", "--build_url", help="github action test build url.")
@click.option("-n", "--network", type=click.Choice(EnvName), default=EnvName.NIGHT_STAND.value,
              help="In which stand run tests")
@click.option("--test-group", help="Name of the failed test group")
def send_notification(url, build_url, network, test_group: str):
    slack_notification = SlackNotification()

    # build info
    parsed_build_url = urlparse(build_url).path.split("/")
    build_id = parsed_build_url[-1]
    build_info = {"id": build_id, "url": build_url}

    # failed tests group or count if available
    failed_count_by_group: defaultdict[TestGroup, int] = error_log.get_count_by_group()
    if failed_count_by_group:
        failed_tests = "\n".join(f"{group}: {count}" for group, count in failed_count_by_group.items())
    else:
        failed_tests = test_group

    # Allure report url
    try:
        with Path(ALLURE_REPORT_URL).open() as f:
            allure_report_url = f.read()
    except FileNotFoundError:
        allure_report_url = ""

    # add combined block
    slack_notification.add_combined_block(
        build_info=build_info,
        network=network,
        failed_tests=failed_tests,
        report_url=allure_report_url,
        comments=error_log.read().comments,
    )

    # add the divider
    slack_notification.add_divider()

    # send the notification
    payload = slack_notification.model_dump_json()
    response = requests.post(url=url, data=payload)
    if response.status_code != 200:
        click.echo(f"Response status code: {response.status_code}")
        click.echo(f"Response status code: {response.text}")
        click.echo(f"Payload: {payload}")
        raise RuntimeError(f"Notification is not sent. Error: {response.text}")


@cli.command(name="get-balances", help="Get operator balances in NEON and SOL")
@click.option("-n", "--network", default="night-stand", type=str, help="In which stand run tests")
def get_operator_balances(network: str):
    net = network_manager.get_network_object(network)
    operator = Operator(
        net["proxy_url"],
        net["solana_url"],
        net["spl_neon_mint"],
        evm_loader=net["evm_loader"]
    )
    neon_balance = operator.get_token_balance()
    sol_balance = operator.get_solana_balance()
    print(
        f'Operator balances ({len(net["operator_keys"])}):\n'
        f"NEON: {neon_balance}\n"
        f"SOL: {sol_balance / 1_000_000_000}"
    )


@cli.group("infra", help="Manage test infrastructure")
def infra():
    pass


@infra.command(name="deploy", help="Deploy test infrastructure")
@click.option("--current_branch", help="Branch of neon-tests repository")
@click.option("--head_branch", default="", help="Feature branch name")
@click.option("--base_branch", default="", help="Target branch of the pull request")
@click.option("--use-real-price", required=False, default="0", help="Remove CONST_GAS_PRICE from proxy")
def deploy(current_branch, head_branch, base_branch, use_real_price):
    # use feature branch or version tag as tag for proxy, evm and faucet images or use latest
    proxy_tag, evm_tag, faucet_tag = "", "", ""

    if '/merge' not in current_branch and current_branch != "develop":
        proxy_tag = current_branch if is_branch_exist(PROXY_GITHUB_URL, current_branch) else ""
        evm_tag = current_branch if is_branch_exist(NEON_EVM_GITHUB_URL, current_branch) else ""
        faucet_tag = current_branch if is_branch_exist(FAUCET_GITHUB_URL, current_branch) else ""

    elif head_branch:
        proxy_tag = head_branch if is_branch_exist(PROXY_GITHUB_URL, head_branch) else ""
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
    use_real_price = True if use_real_price == "1" else False

    evm_branch = evm_tag if evm_tag != "latest" else "develop"
    proxy_branch = proxy_tag if proxy_tag != "latest" else "develop"

    infrastructure.deploy_infrastructure(evm_tag, proxy_tag, faucet_tag, evm_branch, proxy_branch, use_real_price)


@infra.command(name="destroy", help="Destroy test infrastructure")
def destroy():
    infrastructure.destroy_infrastructure()


@infra.command(name="download-logs", help="Download remote docker logs")
def download_logs():
    infrastructure.download_remote_docker_logs()


@infra.command(name="gen-accounts", help="Setup accounts with balance")
@click.option("-c", "--count", default=2, help="How many users prepare")
@click.option("-a", "--amount", default=10000, help="How many airdrop")
@click.option("-n", "--network", default="night-stand", type=str, help="In which stand run tests")
def prepare_accounts(count, amount, network):
    infrastructure.prepare_accounts(network, count, amount)


@infra.command("print-network-param")
@click.option("-n", "--network", default="night-stand", type=str, help="In which stand run tests")
@click.option("-p", "--param", type=str, help="any network param like proxy_url, network_id e.t.c")
def print_network_param(network, param):
    network_manager = NetworkManager(network)
    print(network_manager.get_network_param(network, param))


infra.add_command(deploy, "deploy")
infra.add_command(destroy, "destroy")
infra.add_command(download_logs, "download-logs")
infra.add_command(prepare_accounts, "gen-accounts")
infra.add_command(print_network_param, "print-network-param")


@cli.group("dapps", help="Manage dapps")
def dapps():
    pass


@dapps.command("save_dapps_cost_report_to_db", help="Save dApps Cost Report to db")
@click.option("-d", "--directory", default="reports", help="Directory with reports")
@click.option("--repo", type=click.Choice(tp.get_args(RepoType)), required=True)
@click.option("--evm_tag", required=True)
@click.option("--proxy_tag", required=True)
@click.option("--evm_commit_sha", required=True)
@click.option("--proxy_commit_sha", required=True)
def save_dapps_cost_report_to_db(
        directory: str,
        repo: RepoType,
        evm_tag: str,
        proxy_tag: str,
        evm_commit_sha: str,
        proxy_commit_sha: str,
):
    tag = evm_tag if repo == "evm" else proxy_tag

    report_data = dapps_cli.prepare_report_data(directory)
    db = PostgresTestResultsHandler()

    # define if previous similar reports should be deleted
    is_neon_evm_tag_version_branch = bool(re.fullmatch(VERSION_BRANCH_TEMPLATE, evm_tag))
    is_proxy_tag_version_branch = bool(re.fullmatch(VERSION_BRANCH_TEMPLATE, proxy_tag))

    if evm_tag == proxy_tag == "latest":
        click.echo("This is a merge to develop")
        do_delete = False
    elif is_neon_evm_tag_version_branch and is_proxy_tag_version_branch and evm_tag == proxy_tag:
        click.echo(f"This is a merge to version branch {evm_tag}")
        do_delete = False
    else:
        do_delete = True

    # delete them if needed
    if do_delete:
        report_ids_old = db.get_cost_report_ids(repo=repo, tag=tag)
        if report_ids_old:
            db.delete_data_by_report_ids(report_ids=report_ids_old)
            db.delete_reports(report_ids=report_ids_old)

    # save the new report
    report_id_new = db.save_cost_report(
        repo=repo,
        neon_evm_tag=evm_tag,
        proxy_tag=proxy_tag,
        evm_commit_sha=evm_commit_sha,
        proxy_commit_sha=proxy_commit_sha,
    )
    db.save_cost_report_data(report_data=report_data, cost_report_id=report_id_new)


@dapps.command("save_dapps_cost_report_to_md", help="Save dApps Cost Report to cost_reports.md")
@click.option("-d", "--directory", default="reports", help="Directory with reports")
def save_dapps_cost_report_to_md(directory: str):
    report_data = dapps_cli.prepare_report_data(directory)

    # Add 'gas_used_%' column after 'gas_used'
    report_data.insert(
        report_data.columns.get_loc("gas_used") + 1,
        "gas_used_%",
        (report_data["gas_used"] / report_data["gas_estimated"]) * 100,
    )
    report_data["gas_used_%"] = report_data["gas_used_%"].round(2)

    # Dump report_data DataFrame to markdown, grouped by the dApp
    report_as_markdown_table = dapps_cli.report_data_to_markdown(df=report_data)
    Path("cost_reports.md").write_text(report_as_markdown_table)


@dapps.command("compare_dapp_cost_reports", help="Compare dApp results")
@click.option("--repo", type=click.Choice(tp.get_args(RepoType)), required=True)
@click.option("--evm_tag", required=True)
@click.option("--proxy_tag", required=True)
@click.option("--version_branch", required=True)
@click.option("--history_depth_limit", type=int, help="How many runs to include into statistical analysis")
def compare_dapp_results(
        repo: RepoType,
        evm_tag: str,
        proxy_tag: str,
        version_branch: str,
        history_depth_limit: int,
):
    """
    >>> compared_service_tag
    v1.1.1 - GitHub tag
    feature_foo - feature branch

    >>> other_service_tag
    v1.1.x - version branch
    feature_foo - feature branch
    latest - develop branch
    """
    click.echo(f"compare_dapp_results: {locals()}")

    compared_service_tag = evm_tag if repo == "evm" else proxy_tag
    other_service_tag = evm_tag if repo == "proxy" else proxy_tag
    db = PostgresTestResultsHandler()

    # define the tags against which the comparison will be done
    previous_tags: list[str]

    if re.fullmatch(GITHUB_TAG_PATTERN, compared_service_tag):
        previous_tags = db.get_previous_tags(
            repo=repo,
            tag=compared_service_tag,
            limit=history_depth_limit,
        )
    else:
        if version_branch:
            previous_tags = [version_branch]
        else:
            previous_tags = ["latest"]

    click.echo(f"previous_tags: {previous_tags}")

    historical_data = db.get_historical_data(
        depth=history_depth_limit,
        repo=repo,
        latest_tag=compared_service_tag,
        previous_tags=previous_tags,
    )

    # get commit sha for compared_service and other_service
    data_sample_row = historical_data[
        (historical_data["repo"] == repo) &
        (historical_data["neon_evm_tag"] == evm_tag) &
        (historical_data["proxy_tag"] == proxy_tag)
        ].iloc[0]

    if repo == "evm":
        compared_service_commit_sha = data_sample_row["evm_commit_sha"]
        other_service_commit_sha = data_sample_row["proxy_commit_sha"]
    elif repo == "proxy":
        compared_service_commit_sha = data_sample_row["proxy_commit_sha"]
        other_service_commit_sha = data_sample_row["evm_commit_sha"]
    else:
        raise ValueError(f'Unknown repo "{repo}"')

    compared_service_sha_string = f", commit sha {compared_service_commit_sha}" if compared_service_commit_sha else ""
    other_service_sha_string = f", commit sha {other_service_commit_sha}" if other_service_commit_sha else ""

    # generate plots and save to pdf
    other_service_name = "neon_evm" if repo == "proxy" else "proxy"
    test_results_handler = TestResultsHandler()
    test_results_handler.generate_and_save_plots_pdf(
        historical_data=historical_data,
        title_end=f"on {repo}:{compared_service_tag}{compared_service_sha_string}\n"
                  f"with {other_service_name}:{other_service_tag}{other_service_sha_string}",
        output_pdf="cost_reports.pdf",
    )


@dapps.command("add_pr_comment", help="Add PR comment with dApp cost reports")
@click.option("--pr_url_for_report", default="", help="Url to send the report as comment for PR")
@click.option("--token", default="", help="github token")
@click.option("--md_file", help="File with markdown for the comment")
def add_pr_comment(pr_url_for_report: str, token: str, md_file: str):
    gh_client = GithubClient(token=token)
    gh_client.delete_last_comment(pr_url_for_report)

    with open(md_file) as f:
        markdown = f.read()

    gh_client.add_comment_to_pr(pr_url_for_report, markdown)


@cli.group()
@click.pass_context
def k6(ctx):
    """Commands for k6 load tests."""


@k6.command("build", help="Prepare k6 performance test")
@click.option("-t", "--tag", default="05e0ce5", help="Eth plugin tag or commit sha to use")
@catch_traceback
def build(tag):
    xk6_install = 'go install go.k6.io/xk6/cmd/xk6@latest'
    xk6_build = f'xk6 build --with github.com/szkiba/xk6-prometheus --with github.com/neonlabsorg/xk6-ethereum@{tag}'

    command_install = subprocess.run(xk6_install, shell=True)

    if command_install.returncode != 0:
        sys.exit(command_install.returncode)

    command_build = subprocess.run(xk6_build, shell=True)
    if command_build.returncode != 0:
        sys.exit(command_build.returncode)


@k6.command("run", help="Run k6 performance test")
@click.option("-n", "--network", default="local", help="Which network to use for envs assignment")
@click.option("-s", "--script", default="./loadtesting/k6/tests/sendNeon.test.js", help="Path to k6 script")
@catch_traceback
def run(network, script):
    with open('envs.json') as json_file:
        config = json.load(json_file)
    if os.environ.get('PROXY_URL') is None:
        os.environ["PROXY_URL"] = config[network]['proxy_url']

    if os.environ.get('SOLANA_URL') is None:
        os.environ["SOLANA_URL"] = config[network]['solana_url']

    if os.environ.get('FAUCET_URL') is None:
        os.environ["FAUCET_URL"] = config[network]['faucet_url']

    os.environ["TRACER_URL"] = config[network]['tracer_url']
    os.environ["SPL_NEON_MINT"] = config[network]['spl_neon_mint']
    os.environ["NEON_ERC20_WRAPPER_ADDRESS"] = config[network]['neon_erc20wrapper_address']
    os.environ["NETWORK_ID"] = str(config[network]['network_ids']['neon'])
    
    command = f'./k6 run {script}'
    command_run = subprocess.run(command, shell=True)
    if command_run.returncode != 0:
        sys.exit(command_run.returncode)


if __name__ == "__main__":
    cli()
