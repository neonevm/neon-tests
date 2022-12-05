#!/usr/bin/env python3
import functools
import glob
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import typing as tp
from collections import defaultdict
from multiprocessing.dummy import Pool
from urllib.parse import urlparse


try:
    import click
except ImportError:
    print("Please install click library: pip install click==8.0.3")
    sys.exit(1)

try:
    import requests
    import tabulate

    from utils import web3client
    from utils import faucet
    from utils import cloud
    from utils.operator import Operator
    from utils.web3client import NeonWeb3Client
    from utils.helpers import get_sol_price

    from deploy.cli import dapps as dapps_cli
    from deploy.cli import faucet as faucet_cli
    from deploy.infra.utils import docker as docker_utils
    from deploy.infra.utils import env
except ImportError:
    pass


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

DST_ALLURE_CATEGORIES = pathlib.Path("./allure-results/categories.json")

BASE_EXTENSIONS_TPL_DATA = "ui/extensions/data"

EXTENSIONS_PATH = "ui/extensions/chrome/plugins"
EXTENSIONS_USER_DATA_PATH = "ui/extensions/chrome"

EXPANDED_ENVS = [
    "PROXY_URL",
    "NETWORK_ID",
    "FAUCET_URL",
    "SOLANA_URL",
]

NETWORK_NAME = os.environ.get("NETWORK_NAME", "full_test_suite")

DEVBOX_DOCKERFILE = "deploy/infra/Dockerfile"

DEVBOX_NAME = "neontests-devbox"

# Docker devbox options:
DEVBOX_SSH_PORT_ON_HOST = 8022

HOME_DIR = pathlib.Path(__file__).absolute().parent

OZ_BALANCES = "./compatibility/results/oz_balance.json"


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


def check_profitability(func: tp.Callable) -> tp.Callable:
    """Calculate profitability of OZ cases"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> None:
        def get_tokens_balances(operator: Operator) -> tp.Dict:
            """Return tokens balances"""
            return dict(neon=operator.get_neon_balance(), sol=operator.get_solana_balance() / 1_000_000_000)

        def float_2_str(d):
            return dict(map(lambda i: (i[0], str(i[1])), d.items()))

        if os.environ.get("PROXY_URL") is None:
            network = networks[args[0]]
            op = Operator(
                network["proxy_url"],
                network["solana_url"],
                network["network_id"],
                network["operator_neon_rewards_address"],
                network["spl_neon_mint"],
                network["operator_keys"],
                web3_client=NeonWeb3Client(network["proxy_url"], network["network_id"], session=requests.Session()),
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
            path = pathlib.Path(OZ_BALANCES)
            path.absolute().parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as fd:
                balances = dict(pre=float_2_str(pre), after=float_2_str(after), profitability=float_2_str(profitability))
                json.dump(balances, fp=fd, indent=4, sort_keys=True)
        else:
            func(*args, **kwargs)
    return wrapper


@check_profitability
def run_openzeppelin_tests(network, jobs=8, amount=20000, users=8):
    print(f"Running OpenZeppelin tests in {jobs} jobs on {network}")
    cwd = (pathlib.Path().parent / "compatibility/openzeppelin-contracts").absolute()
    if not list(cwd.glob("*")):
        subprocess.check_call("git submodule init && git submodule update", shell=True, cwd=cwd)
    subprocess.check_call("npx hardhat compile", shell=True, cwd=cwd)
    (cwd.parent / "results").mkdir(parents=True, exist_ok=True)
    keys_env = [
        faucet_cli.prepare_wallets_with_balance(networks[network], count=users, airdrop_amount=amount)
        for i in range(jobs)
    ]

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


def print_oz_balances():
    """Print token balances after oz tests"""
    path = pathlib.Path(OZ_BALANCES)
    if not path.exists():
        print(red(f"OZ balances report not found on `{path.resolve()}` !"))
        return

    with open(path, "r") as fd:
        balances = json.load(fd)
    report = tabulate.tabulate(
        [
            ["NEON", balances["pre"]["neon"], balances["after"]["neon"], balances["profitability"]["neon"]],
            ["SOL", balances["pre"]["sol"], balances["after"]["sol"], balances["profitability"]["sol"]],
        ],
        headers=["token", "on start balance", "os stop balance", "P/L (USD)"],
        tablefmt="fancy_outline",
        numalign="right",
        floatfmt=".2f",
    )
    print(green("\nOZ tests suite profitability:"))
    print(yellow(report))


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
@click.option("-n", "--network", default="night-stand", type=str, help="In which stand run tests")
@click.option("-j", "--jobs", default=8, help="Number of parallel jobs (for openzeppelin)")
@click.option("-a", "--amount", default=200000, help="Requested amount from faucet")
@click.option("-u", "--users", default=8, help="Accounts numbers used in OZ tests")
@click.option("--ui-item", default="all", type=click.Choice(["faucet", "neonpass", "all"]), help="Which UI test run")
@click.argument("name", required=True, type=click.Choice(["economy", "basic", "oz", "ui"]))
@catch_traceback
def run(name, jobs, ui_item, amount, users, network):
    if not network and name == "ui":
        network = "devnet"
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
    print_oz_balances()


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
    "-u", "--users", default=50, type=int, help="Peak number of concurrent Locust users.", show_default=True
)

locust_rate = click.option(
    "-r", "--spawn-rate", default=1, type=int, help="Rate to spawn users at (users per second)", show_default=True
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
    base_path = pathlib.Path(__file__).parent
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
    base_path = pathlib.Path(__file__).parent
    path = base_path / "loadtesting/tracerapi/prepare_data/locustfile.py"
    if not (path.exists() and path.is_file()):
        raise FileNotFoundError(f"path doe's not exists. {path.resolve()}")
    command = f"locust -f {path.absolute()} --host={host} --users={users} --spawn-rate={spawn_rate} --headless"
    if credentials:
        command += f" --credentials={credentials}"
    else:
        command += f" --credentials={base_path.absolute()}/loadtesting/tracerapi/envs.json"
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


@cli.command(help="Download allure history")
@click.argument("name", type=click.STRING)
@click.option("-n", "--network", default="night-stand", type=str, help="In which stand run tests")
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
@click.option("-n", "--network", default="night-stand", type=str, help="In which stand run tests")
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
@click.option("-t", "--traceback", default="", help="custom traceback message.")
@click.option("-n", "--network", default="night-stand", type=str, help="In which stand run tests")
def send_notification(url, build_url, traceback, network):
    p = pathlib.Path(f"./{CMD_ERROR_LOG}")
    trace_back = traceback or (p.read_text() if p.exists() else "")
    # Slack has 3001 symbols limit
    if len(trace_back) > 2500:
        trace_back = trace_back[0:2500]
    tpl = ERR_MSG_TPL.copy()

    parsed_build_url = urlparse(build_url).path.split("/")
    build_id = parsed_build_url[-1]
    repo_name = f"{parsed_build_url[1]}/{parsed_build_url[2]}"
    tpl["blocks"][0]["text"]["text"] = (
        f"*Build <{build_url}|`{build_id}`> of repository `{repo_name}` is failed on `{network}`!* \n{trace_back}"
        f"\n<{build_url}|View build details>"
    )
    response = requests.post(url=url, data=json.dumps(tpl))
    if response.status_code != 200:
        click.echo(f"Response status code: {response.status_code}")
        click.echo(f"TPL: {json.dumps(tpl)}")
        raise RuntimeError(f"Notification is not sent. Error: {response.text}")


@cli.group("infra", help="Manage test infrastructure")
def infra():
    pass


@infra.command(name="deploy", help="Deploy test infrastructure")
def deploy():
    dapps_cli.deploy_infrastructure()


@infra.command(name="destroy", help="Destroy test infrastructure")
def destroy():
    dapps_cli.destroy_infrastructure()


@infra.command(name="gen-accounts", help="Setup accounts with balance")
@click.option("-c", "--count", default=2, help="How many users prepare")
@click.option("-a", "--amount", default=10000, help="How many airdrop")
def prepare_accounts(count, amount):
    dapps_cli.prepare_accounts(count, amount)


infra.add_command(deploy, "deploy")
infra.add_command(destroy, "destroy")
infra.add_command(prepare_accounts, "gen-accounts")


@cli.group("dapps", help="Manage dapps")
def dapps():
    pass


@dapps.command("report", help="Print dapps report (from .json files)")
@click.option("-d", "--directory", default="reports", help="Directory with reports")
def make_dapps_report(directory):
    dapps_cli.print_report(directory)


@cli.group("devbox", help="Manage devbox infrastructure")
def devbox():
    """Commands for devbox manipulation."""


@devbox.command("rm")
def rm():
    """Terminate existing devbox."""
    if env.is_devbox():
        return print(env.green("You inside `devbox` first quit"))
    if docker_utils.docker_inspect(DEVBOX_NAME):
        env.shell(f"docker rm -f {DEVBOX_NAME}")
        print(env.green("Terminated devbox"))
    else:
        print(env.green("DevBox not running, nothing to terminate"))


@devbox.command("build")
@click.option(
    "-p",
    "--image-path",
    "image_path",
    type=str,
    default=DEVBOX_DOCKERFILE,
    help="Build image Dockerfile relative path.",
)
@click.option(
    "-n",
    "--image-name",
    "image_name",
    type=str,
    default=DEVBOX_NAME,
    help="Build image name.",
)
@click.option(
    "-t",
    "--tag",
    "tag",
    type=str,
    default="latest",
    help="Build image tag.",
)
@click.option(
    "--quick/--full",
    default=None,
    help="Quick mode (Default). In quick mode task for sake of speed ignore some extra checks, "
    "which might produce stale artifacts. Full mode builds eveything without Docker cache, "
    "and because of this sick from duplicate layers for the same Dockerfile steps. "
    "WARN: It's still unclear do we really need this CLI option. Strong argument against "
    "is that `docker build --pull` invalidates the whole cache tree every time the base "
    "buster/alpine image got updated. Base images get their security patches nearly every day. "
    "As a side effect of these updates we check very frequency our images on nocache build, and may "
    "find and address any issues early.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Dry run")
def build(image_path, image_name, tag, quick, dry_run=None):
    """Build devbox docker image."""
    if env.is_devbox():
        return print(env.green("`devbox` is built, exiting "))
    env.header("Prepare docker images build...")
    image = docker_utils.Image(pathlib.Path(image_path), image_name, tag)
    build_args = ()
    if quick is None:
        # Quick by default
        quick = True

    if dry_run:
        return print(env.yellow("Dry run, exiting"))

    image.build(cache=quick, build_args=build_args)


def create_devbox(prefix="", tag="latest"):

    box_name = DEVBOX_NAME
    network_name = "neon-tests"
    cwd = os.getcwd()
    workspace = "/neon-tests"
    provide_ssh_port = f"{DEVBOX_SSH_PORT_ON_HOST}:22"
    prefix = prefix or docker_utils.IMAGE_PREFIX

    if not docker_utils.docker_inspect(box_name):
        box_image = f"{prefix}/{box_name}:{tag}"
        if not docker_utils.docker_image_exists(box_image):
            print(env.yellow(f"No {box_image} image found, run `devbox build` command"))
            exit()
        # Run devbox in user-defined network and link it for test containers
        if not docker_utils.docker_inspect_network(network_name):
            env.shell(f"docker network create {network_name}")

        home = os.path.expanduser("~")

        def var_args():
            """Variatic arguments"""
            args = []

            # neon client
            neon_cli_path = f"{cwd}/deploy/infra/tools/neon-cli"
            if os.path.isfile(neon_cli_path):
                args.append(f"-v {neon_cli_path}:/usr/local/bin/neon-cli")
            else:
                print(env.yellow(f"copy file `neon-cli` to {neon_cli_path} for load tests to work properly"))
            # solana operator keys
            operator_keys_path = f"{cwd}/loadtesting/synthetic/operator-keypairs"
            if os.path.exists(operator_keys_path):
                args.append(f"-v {operator_keys_path}:/root/.config/solana")
            else:
                print(env.yellow(f"copy solana operator keys to {operator_keys_path} for load tests to work properly"))
            # pip/pip-tools cache
            if os.path.exists(f"{home}/.cache"):
                args.append(f"-v {home}/.cache:/root/.cache")

            # git config
            if os.path.exists(f"{home}/.gitconfig"):
                args.append(f"-v {home}/.gitconfig:/root/.gitconfig")

            # ssh
            if os.path.exists(f"{home}/.ssh"):
                args.append(f"-v {home}/.ssh:/root/.ssh")
            # pass ssh-agent to container
            if "SSH_AUTH_SOCK" in os.environ and platform.system() == "Linux":
                args.append(f" -v {os.environ['SSH_AUTH_SOCK']}:/ssh-agent -e SSH_AUTH_SOCK=/ssh-agent ")
            elif platform.system() == "Darwin":
                sock_path = os.environ.get("SSH_AUTH_SOCK", "/run/host-services/ssh-auth.sock")
                args.append(f" --mount type=bind,src={sock_path},target=/ssh-agent -e " "SSH_AUTH_SOCK=/ssh-agent ")

            shell_history_path = f"{cwd}/deploy/infra/devbox/.bash_history"
            # Ensure .bash_history exists
            env.shell(f"touch {shell_history_path}")
            args.append(f"-v {shell_history_path}:/root/.bash_history")

            return " ".join(args)

        # Start new
        env.shell(
            "docker run --rm -it -d --init"
            f" --name={box_name}"
            f" --network={network_name}"
            f" -e DEVBOX=true"
            f" -e DEVBOX_NETWORK={network_name}"
            f" -e DEVBOX_CWD={cwd}"
            f" -w {workspace}"
            f" -v {cwd}:{workspace}"
            # SSH for remote debugging
            f" -p {provide_ssh_port}" f" -v {cwd}/deploy/infra/devbox/ssh/id_ed25519.pub:/root/.ssh/authorized_keys"
            # Bash profile and history
            f" -v {cwd}/deploy/infra/devbox/.bash-profile:/etc/profile.d/neontests.sh"
            # Docker host socket
            " -v /var/run/docker.sock:/var/run/docker.sock"
            # For pytest fileutil mount shared fixtures
            " -v /tmp:/tmp" f" {var_args()} {box_image} {workspace}/deploy/infra/devbox/startup.sh",
            capture=True,
        )
        print(env.green("Started devbox"))
    else:
        print(env.green("Devbox already started, attaching"))
    return box_name


@devbox.command("up")
def up():
    """Start new devbox or attach existing."""
    if env.is_devbox():
        return print(env.green("`devbox` is created, exiting "))
    box_name = create_devbox()
    # Attach to running container
    env.shell(f"docker exec -it {box_name} bash --login; exit 0")


if __name__ == "__main__":
    cli()
