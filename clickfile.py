#!/usr/bin/env python3
import functools
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import typing as tp
from multiprocessing.dummy import Pool
from pathlib import Path

import pytest

from utils.consts import EnvName, TEST_GROUPS, EXTERNAL_CONTRACT_PATH
from utils.evm_loader import EvmLoader
from utils.types import TestGroup

try:
    import click
    import requests
    import tabulate
    import yaml
except ImportError:
    print("Please install dependencies: pip3 install -r deploy/requirements/click.txt")
    sys.exit(1)

try:
    from deploy.cli.network_manager import NetworkManager
    from utils.error_log import error_log
    from utils import create_allure_environment_opts, time_measure
    from deploy.cli import infrastructure
    from utils import web3client
    from utils.operator import Operator
    from utils.prices import get_sol_price_with_retry
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
VERSION_BRANCH_TEMPLATE = r"[vt]{1}\d{1,2}\.\d{1,2}\.x.*"
GITHUB_TAG_PATTERN = re.compile(r"^[vt]\d{1,2}\.\d{1,2}\.\d{1,2}$")


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
        network_manager = NetworkManager()
        network = network_manager.get_network_object(args[0])
        w3client = web3client.NeonChainWeb3Client(network["proxy_url"])
        evm_loader = EvmLoader(
            program_id=network["evm_loader"],
            endpoint=network["solana_url"],
            neon_chain_id=network["network_ids"]["neon"],
            sol_chain_id=network["network_ids"]["sol"],
            neon_token_mint_str=network["spl_neon_mint"],
        )

        def get_tokens_balances(operator: Operator) -> tp.Dict:
            """Return tokens balances"""
            return dict(
                neon=w3client.to_main_currency(operator.get_token_balance(w3client)),
                sol=operator.get_solana_balance() / 1_000_000_000,
            )

        def float_2_str(d):
            return dict(map(lambda i: (i[0], str(i[1])), d.items()))

        if os.environ.get("OZ_BALANCES_REPORT_FLAG") is not None:
            op = Operator(evm_loader)
            pre = get_tokens_balances(op)
            try:
                func(*args, **kwargs)
            except subprocess.CalledProcessError:
                pass
            after = get_tokens_balances(op)
            profitability = dict(
                neon=round(float(after["neon"] - pre["neon"]) * 0.25, 2),
                sol=round((float(pre["sol"] - after["sol"])) * get_sol_price_with_retry(), 2),
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
    network_manager = NetworkManager()
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
        "NEON_CORE.Version": web3_client.get_neon_core_version()["result"],
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
    network_manager = NetworkManager()
    settings = network_manager.get_network_object(network)
    web3_client = web3client.NeonChainWeb3Client(proxy_url=settings["proxy_url"])
    tracer_api = JsonRPCSession(settings["tracer_url"])

    block = web3_client.get_block_number()

    wait_condition(
        lambda: (tracer_api.send_rpc(method="get_neon_revision", params=block)["result"]["neon_revision"]) is not None,
        timeout_sec=180,
    )

    return True


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


@cli.command(help="Download test contracts from neon-contracts repo")
@click.option(
    "--branch",
    default="add/execute-without-lamports",
    help="neon_evm branch name. " "If branch doesn't exist, develop branch will be used",
)
@click.option("--with-uniswap", is_flag=True, default=False, required=False, help="Download uniswap-v3 contracts")
def update_contracts(branch, with_uniswap):
    update_contracts_from_git(HOODIES_CHAINLINK_GITHUB_URL, "hoodies_chainlink", "main")
    update_contracts_from_git(
        "https://github.com/neonevm/neon-contracts.git",
        "neon-contracts",
        branch=branch,
        update_npm=True,
    )

    if with_uniswap:
        update_contracts_from_git("https://github.com/neonlabsorg/Uniswap-V3-NEON.git", "uniswap-v3", branch="main")

        # we replace init_code_hash of a contracts/external/uniswap-v3/contracts/UniswapV3Pool.sol
        # it is calculated for python solc compiler and it is different from uniswap-v3 repository
        # to calculate this hash you can use the method:
        #     function getPoolInitCodeHash() public returns (bytes32) {
        #       return keccak256(type(UniswapV3Pool).creationCode);
        #     }
        pool_addr_path = (
            Path.cwd()
            / "contracts"
            / "external"
            / "uniswap-v3"
            / "contracts"
            / "v3-periphery"
            / "libraries"
            / "PoolAddress.sol"
        )
        replacements = [
            (
                b"0xe34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54",
                b"0xfeca55d18a66e13a3b004f5ea1833d181be8e62d7ac64669f176c76b5a79fc9d",
            ),
        ]
        with open(pool_addr_path, "rb") as file:
            s = file.read()
            print(file.name)
        for f, r in replacements:
            s = s.replace(f, r)
        with open(pool_addr_path, "wb") as file:
            file.write(s)


@cli.command(help="Run any type of tests")
@click.option("-n", "--network", type=click.Choice(EnvName), help="In which stand run tests")
@click.option("-j", "--jobs", default=8, help="Number of parallel jobs (for openzeppelin)")
@click.option("-p", "--numprocesses", help="Number of parallel jobs for basic tests")
@click.option("-a", "--amount", default=20000, help="Requested amount from faucet")
@click.option("-u", "--users", default=8, help="Accounts numbers used in OZ tests")
@click.option("-c", "--case", default="", type=str, help="Specific test case name pattern to run")
@click.option("--marker", help="Run tests by mark")
@click.option("--cost_reports_dir", default="", help="Directory where CostReports will be created")
@click.option(
    "--ui-item",
    default="website",
    type=click.Choice(["faucet", "neonpass", "website"]),
    help="Which UI test run",
)
@click.option(
    "--keep-error-log", is_flag=True, default=False, help=f"Don't clear {error_log.file_path.name} before run"
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
    cost_reports_dir: str,
):
    if not network and name == "ui":
        network = EnvName.DEVNET
    if DST_ALLURE_CATEGORIES.parent.exists():
        shutil.rmtree(DST_ALLURE_CATEGORIES.parent, ignore_errors=True)
    DST_ALLURE_CATEGORIES.parent.mkdir()

    commands = {
        "economy": "py.test integration/tests/economy",
        "basic": "py.test integration/tests/basic --dist loadgroup",
        "tracer": "py.test -n 5 integration/tests/tracer --dist loadscope",
        "services": "py.test integration/tests/services",
        "compiler_compatibility": "py.test integration/tests/compiler_compatibility --dist loadscope",
        "evm": "py.test integration/tests/neon_evm",
        "ui": "pytest ui/tests/",
        "oz": "",  # the command is defined in run_openzeppelin_tests()
    }

    if name not in commands:
        raise click.ClickException(f"Test group '{name}' does not exist.")
    command = commands[name]

    if name == "basic":
        if network == EnvName.MAINNET:
            command += " -m mainnet"
        if network == EnvName.DEVNET:
            command += " --retries 3 --retry-delay 2"

    if name in {"services", "compiler_compatibility", "evm", "basic"} and numprocesses:
        command += f" --numprocesses {numprocesses}"

    UI_TEST_PATHS = {
        "faucet": "test_faucet.py",
        "website": "website_tests/test_website.py",
        "neonpass": "test_neonpass.py",
    }

    if name == "ui":
        if ui_item not in UI_TEST_PATHS:
            raise click.ClickException(f"Invalid UI item '{ui_item}'. Available: {', '.join(UI_TEST_PATHS.keys())}")
        command += UI_TEST_PATHS[ui_item]

    if name == "oz":
        if not keep_error_log:
            error_log.clear()
        run_openzeppelin_tests(network, jobs=int(jobs), amount=int(amount), users=int(users))
        return

    if name == "tracer":
        if network != EnvName.GETH:
            assert wait_for_tracer_service(network)

    if case:
        if " " in case:
            command += f' -vk "{case}"'
        else:
            command += f" -vk {case}"

    if marker:
        if " " in marker:
            command += f' -m "{marker}"'
        else:
            command += f" -m {marker}"

    command += f" -s --network={network} --make-report --test-group {name}"
    if keep_error_log:
        command += " --keep-error-log"
    if cost_reports_dir:
        command += f" --cost_reports_dir {cost_reports_dir}"

    args = shlex.split(command)[1:]
    exit_code = int(pytest.main(args=args))

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


@cli.group("infra", help="Manage test infrastructure")
def infra():
    pass


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
