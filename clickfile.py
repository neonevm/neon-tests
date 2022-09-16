#!/usr/bin/env python3
import functools
import glob
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import typing as tp
from collections import defaultdict
from multiprocessing.dummy import Pool
from urllib.parse import urlparse

import requests

try:
    import click
except ImportError:
    print("Please install click library: pip install click==8.0.3")
    sys.exit(1)

try:
    from utils import web3client
    from utils import faucet
    from utils import cloud
except ImportError:
    pass

from deploy.cli import dapps as dapps_cli
from deploy.cli import faucet as faucet_cli


CMD_ERROR_LOG = "click_cmd_err.log"

ERR_MSG_TPL = {
    "blocks": [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": ""},
        },
        {"type": "divider"},
    ]
}

ERR_MESSAGES = {"run": "Unsuccessful tests executing.", "requirements": "Unsuccessful requirements installation."}

SRC_ALLURE_CATEGORIES = pathlib.Path("./allure/categories.json")
""" Allure report config tpl
"""

DST_ALLURE_CATEGORIES = pathlib.Path("./allure-results/categories.json")
""" Allure report config
"""

BASE_EXTENSIONS_TPL_DATA = "ui/extensions/data"
"""Relative path where ui tests extensions data stored
"""

EXTENSIONS_PATH = "ui/extensions/chrome/plugins"
EXTENSIONS_USER_DATA_PATH = "ui/extensions/chrome"

EXPANDED_ENVS = [
    "PROXY_URL",
    "NETWORK_ID",
    "FAUCET_URL",
    "SOLANA_URL",
]
"""Test environment settings passed to the container
"""

NETWORK_NAME = os.environ.get("NETWORK_NAME", "full_test_suite")
"""Default network name for docker container
"""


def green(s):
    return click.style(s, fg="green")


def yellow(s):
    return click.style(s, fg="yellow")


def red(s):
    return click.style(s, fg="red")


def catch_traceback(func: tp.Callable) -> tp.Callable:
    """Catch traceback to file"""

    def create_report(func_name, exc=None):
        data = ""
        exc = f"\n*Error:* {exc}" if exc else ""
        path = pathlib.Path(CMD_ERROR_LOG)
        if path.exists() and path.stat().st_size != 0:
            with path.open("r") as fd:
                data = f"{fd.read()}\n"
            path.unlink()
        err_msg = f"*{ERR_MESSAGES.get(func_name)}*{exc}\n{data}"
        with open(CMD_ERROR_LOG, "w") as fd:
            fd.write(err_msg)

    @functools.wraps(func)
    def wrap(*args, **kwargs) -> tp.Any:
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            create_report(func.__name__, e)
            raise
        finally:
            e = sys.exc_info()
            if e[0] and e[0].__name__ == "SystemExit" and e[1] != 0:
                create_report(func.__name__)

        return result

    return wrap


networks = []
with open("./envs.json", "r") as f:
    networks = json.load(f)
    if NETWORK_NAME not in networks.keys() and os.environ.get("DUMP_ENVS"):
        environments = defaultdict(dict)
        for var in EXPANDED_ENVS:
            environments[NETWORK_NAME].update({var.lower(): os.environ.get(var, "")})
        networks.update(environments)


def run_openzeppelin_tests(network, jobs=8, amount=20000, users=8):
    print(f"Running OpenZeppelin tests in {jobs} jobs on {network}")
    cwd = (pathlib.Path().parent / "compatibility/openzeppelin-contracts").absolute()
    if not list(cwd.glob("*")):
        subprocess.check_call("git submodule init && git submodule update", shell=True, cwd=cwd)
    subprocess.check_call("npx hardhat compile", shell=True, cwd=cwd)
    (cwd.parent / "results").mkdir(parents=True, exist_ok=True)
    keys_env = [faucet_cli.prepare_wallets_with_balance(networks[network], count=users, airdrop_amount=amount) for i in range(jobs)]

    tests = subprocess.check_output("find \"test\" -name '*.test.js'", shell=True, cwd=cwd).decode().splitlines()

    def run_oz_file(file_name):
        print(f"Run {file_name}")
        keys = keys_env.pop(0)
        env = os.environ.copy()
        env["PRIVATE_KEYS"] = ",".join(keys)
        env["NETWORK_ID"] = str(networks[network]["network_id"])
        env["PROXY_URL"] = networks[network]["proxy_url"]

        out = subprocess.run(f"npx hardhat test {file_name}", shell=True, cwd=cwd, capture_output=True, env=env)
        stdout = out.stdout.decode()
        stderr = out.stderr.decode()
        print(f"Test {file_name} finished with code {out.returncode}")
        print(stdout)
        print(stderr)
        keys_env.append(keys)
        log_dirs = cwd.parent / "results" / file_name.replace(".", "_").replace("/", "_")
        log_dirs.mkdir(parents=True, exist_ok=True)
        with open(log_dirs / "stdout.log", "w") as f:
            f.write(stdout)
        with open(log_dirs / "stderr.log", "w") as f:
            f.write(stderr)

    pool = Pool(jobs)
    pool.map(run_oz_file, tests)
    pool.close()
    pool.join()
    # Add allure environment
    settings = networks[network]
    web3_client = web3client.NeonWeb3Client(settings["proxy_url"], settings["network_id"])
    opts = {
        "Proxy.Version": web3_client.get_proxy_version()["result"],
        "EVM.Version": web3_client.get_evm_version()["result"],
        "CLI.Version": web3_client.get_cli_version()["result"],
    }
    with open("./allure-results/environment.properties", "w+") as f:
        f.write("\n".join(map(lambda x: f"{x[0]}={x[1]}", opts.items())))
        f.write("\n")
    # Add epic name for allure result files
    openzeppelin_reports = pathlib.Path("./allure-results")
    res_file_list = [str(res_file) for res_file in openzeppelin_reports.glob("*-result.json")]
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


def generate_allure_environment(network_name: str):
    network = networks[network_name]
    env = os.environ.copy()
    env["NETWORK_ID"] = str(network["network_id"])
    env["PROXY_URL"] = network["proxy_url"]
    return env


def install_python_requirements():
    command = "pip3 install --upgrade -r deploy/requirements/prod.txt  -r deploy/requirements/devel.txt -r deploy/requirements/ui.txt"
    subprocess.check_call(command, shell=True)
    command = "pip3 install --no-deps -r deploy/requirements/nodeps.txt"
    subprocess.check_call(command, shell=True)


def install_ui_requirements():
    click.echo(green("Install python requirements for Playwright"))
    command = "pip3 install --upgrade -r deploy/requirements/ui.txt"
    subprocess.check_call(command, shell=True)
    # On Linux Playwright require `xclip` to work.
    if sys.platform in ["linux", "linux2"]:
        try:
            command = "apt update && apt install xclip"
            subprocess.check_call(command, shell=True)
        except Exception:
            click.echo(
                red(
                    f"{10*'!'} Warning: Linux requires `xclip` to work. "
                    f"Install with your package manager, e.g. `sudo apt install xclip` {10*'!'}"
                ),
                color=True,
            )
    # install ui test deps,
    # download the Playwright package and install browser binaries for Chromium, Firefox and WebKit.
    click.echo(green("Install browser binaries for Chromium, Firefox and WebKit."))
    subprocess.check_call("playwright install", shell=True)
    click.echo(green("prepare ui tests extensions and extensions user_data"))
    # prepare ui tests extensions and extensions user_data
    base_path = pathlib.Path(__file__).absolute().parent
    for item in (base_path / BASE_EXTENSIONS_TPL_DATA).iterdir():
        if "extension" in item.name:
            cmd = f"tar -xf {item.as_posix()} -C {base_path / EXTENSIONS_PATH}"
        elif "user_data" in item.name:
            cmd = f"tar -xf {item.as_posix()} -C {base_path / EXTENSIONS_USER_DATA_PATH}"
        subprocess.check_call(cmd, shell=True)


def install_oz_requirements():
    cwd = pathlib.Path().absolute() / "compatibility/openzeppelin-contracts"
    if list(cwd.glob("*lock*")):
        cmd = "npm ci"
    else:
        cmd = "npm install npm@latest -g"
    subprocess.check_call(cmd, shell=True, cwd=cwd.as_posix())


@click.group()
def cli():
    pass


@cli.command(help="Update base python requirements")
@click.option(
    "-d", "--dep", default="devel", type=click.Choice(["devel", "python", "oz", "ui"]), help="Which deps install"
)
@catch_traceback
def requirements(dep):
    if dep in ["devel", "python"]:
        install_python_requirements()
    if dep in ["devel", "oz"]:
        install_oz_requirements()
    if dep == "ui":
        install_ui_requirements()


@cli.command(help="Run any type of tests")
@click.option("-n", "--network", default=None, type=click.Choice(networks.keys()), help="In which stand run tests")
@click.option("-j", "--jobs", default=8, help="Number of parallel jobs (for openzeppelin)")
@click.option("-a", "--amount", default=200000, help="Requested amount from faucet")
@click.option("-u", "--users", default=8, help="Accounts numbers used in OZ tests")
@click.option("--ui-item", default="all", type=click.Choice(["faucet", "neonpass", "all"]), help="Which UI test run")
@click.argument("name", required=True, type=click.Choice(["economy", "basic", "oz", "ui"]))
@catch_traceback
def run(name, jobs, ui_item, amount, users, network=None):
    if not network and name == "ui":
        network = "devnet"
    elif not network:
        network = "night-stand"
    if DST_ALLURE_CATEGORIES.parent.exists():
        shutil.rmtree(DST_ALLURE_CATEGORIES.parent, ignore_errors=True)
    DST_ALLURE_CATEGORIES.parent.mkdir()
    if name == "economy":
        command = "py.test integration/tests/economy/test_economics.py"
    elif name == "basic":
        command = "py.test integration/tests/basic"
    elif name == "oz":
        run_openzeppelin_tests(network, jobs=int(jobs), amount=int(amount), users=int(users))
        shutil.copyfile(SRC_ALLURE_CATEGORIES, DST_ALLURE_CATEGORIES)
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

    command += f" -s --network={network} --make-report"
    cmd = subprocess.run(command, shell=True)
    shutil.copyfile(SRC_ALLURE_CATEGORIES, DST_ALLURE_CATEGORIES)

    if cmd.returncode != 0:
        sys.exit(cmd.returncode)


@cli.command(help="Summarize openzeppelin tests results")
def ozreport():
    test_report, skipped_files = parse_openzeppelin_results()
    print_test_suite_results(test_report, skipped_files)


@cli.command(help="Run `neon` pipeline performance test")
@click.option(
    "-f",
    "--locustfile",
    type=str,
    default="loadtesting/locustfile.py",
    help="Python module to import. It's sub-folder and file name.",
    show_default=True,
)
@click.option(
    "-c",
    "--credentials",
    type=str,
    help="Relative path to credentials module.",
    show_default=True,
)
@click.option(
    "-h",
    "--host",
    default="night-stand",
    type=click.Choice(networks),
    help="In which stand run tests.",
    show_default=True,
)
@click.option("-u", "--users", default=10, type=int, help="Peak number of concurrent Locust users.", show_default=True)
@click.option(
    "-r", "--spawn-rate", default=1, type=int, help="Rate to spawn users at (users per second)", show_default=True
)
@click.option(
    "-t",
    "--run-time",
    type=int,
    help="Stop after the specified amount of time, e.g. (300s, 20m, 3h, 1h30m, etc.). "
    "Only used together without Locust Web UI. [default: always run]",
)
@click.option(
    "-T",
    "--tag",
    type=str,
    multiple=True,
    help="tag to include in the test, so only tasks " "with any matching tags will be executed",
)
@click.option(
    "--web-ui/--headless",
    " /-w",
    default=True,
    help="Enable the web interface. " "If UI is enabled, go to http://0.0.0.0:8089/ [default: `Web UI is enabled`]",
)
def locust(locustfile, credentials, host, users, spawn_rate, run_time, tag, web_ui):
    """Run `Neon` pipeline performance test

    path it's sub-folder and file name  `loadtesting/locustfile.py`.
    """
    path = pathlib.Path(__file__).parent / locustfile
    if not (path.exists() and path.is_file()):
        raise FileNotFoundError(f"path doe's not exists. {path.resolve()}")
    command = f"locust -f {path.as_posix()} --host={host} --users={users} --spawn-rate={spawn_rate}"
    if credentials:
        command += f" --credentials={credentials}"
    if run_time:
        command += f" --run-time={run_time}"
    if tag:
        command += f" --tags {' '.join(tag)}"
    if not web_ui:
        command += f" --headless"

    cmd = subprocess.run(command, shell=True)

    if cmd.returncode != 0:
        sys.exit(cmd.returncode)


@cli.command(help="Download allure history")
@click.argument("name", type=click.STRING)
@click.option(
    "-n", "--network", default="night-stand", type=click.Choice(networks.keys()), help="In which stand run tests"
)
@click.option("-d", "--destination", default="./allure-results", type=click.Path(file_okay=False, dir_okay=True))
def get_allure_history(name: str, network: str, destination: str = "./allure-results"):
    branch = os.environ.get("GITHUB_REF_NAME")
    path = pathlib.Path(name) / network / branch

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
        cloud.download(path / str(max(runs)) / "history", pathlib.Path(destination) / "history")


@cli.command(help="Upload allure report")
@click.argument("name", type=click.STRING)
@click.option(
    "-n", "--network", default="night-stand", type=click.Choice(networks.keys()), help="In which stand run tests"
)
@click.option("-s", "--source", default="./allure-report", type=click.Path(file_okay=False, dir_okay=True))
def upload_allure_report(name: str, network: str, source: str = "./allure-report"):
    branch = os.environ.get("GITHUB_REF_NAME")
    build_id = os.environ.get("GITHUB_RUN_NUMBER")
    path = pathlib.Path(name) / network / branch
    cloud.upload(source, path / build_id)
    report_url = f"http://neon-test-allure.s3-website.eu-central-1.amazonaws.com/{path / build_id}"
    with open("/tmp/index.html", "w") as f:
        f.write(
            f"""<!DOCTYPE html><meta charset="utf-8"><meta http-equiv="refresh" content="0; URL={report_url}">
        <meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">
        """
        )
    cloud.upload("/tmp/index.html", path)
    print(f"Allure report link: {report_url}")


@cli.command(help="Send notification to slack")
@click.option("-u", "--url", help="slack app endpoint url.")
@click.option("-b", "--build_url", help="github action test build url.")
def send_notification(url, build_url):
    p = pathlib.Path(f"./{CMD_ERROR_LOG}")
    trace_back = p.read_text() if p.exists() else ""
    tpl = ERR_MSG_TPL.copy()

    parsed_build_url = urlparse(build_url).path.split("/")
    build_id = parsed_build_url[-1]
    repo_name = f"{parsed_build_url[1]}/{parsed_build_url[2]}"

    tpl["blocks"][0]["text"]["text"] = (
        f"*Build <{build_url}|`{build_id}`> of repository `{repo_name}` is failed.* \n{trace_back}"
        f"\n<{build_url}|View build details>"
    )
    requests.post(url=url, data=json.dumps(tpl))


@cli.group("infra", help="Manage test infrastructure")
def infra():
    pass


@infra.command(name="deploy", help="Deploy test infrastructure")
def deploy():
    dapps_cli.deploy_infrastructure()


@infra.command(name="destroy", help="Destroy test infrastructure")
def destroy():
    dapps_cli.destroy_infrastructure()


@infra.command(name="prepare-accounts", help="Setup accounts with balance")
@click.option("-c", "--count", default=2, help="How many users prepare")
@click.option("-a", "--amount", default=10000, help="How many airdrop")
def prepare_accounts(count, amount):
    network = {
        "proxy_url": f"http://{os.environ.get('PROXY_IP')}:9090/solana",
        "network_id": 111,
        "solana_url": f"http://{os.environ.get('SOLANA_IP')}:8899/",
        "faucet_url": f"http://{os.environ.get('PROXY_IP')}:3333/",
    }
    accounts = faucet_cli.prepare_wallets_with_balance(
        network, count, amount
    )
    if os.environ.get("CI"):
        subprocess.run(f'echo "::set-output name=accounts::{",".join(accounts)}"')


infra.add_command(deploy, "deploy")
infra.add_command(destroy, "destroy")
infra.add_command(prepare_accounts)


if __name__ == "__main__":
    cli()
