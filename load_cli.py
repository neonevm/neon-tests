#!/usr/bin/env python3
import functools
import os
import subprocess
import sys
import typing as tp
from pathlib import Path

import click
from deploy.cli.network_manager import NetworkManager
from utils.accounts import EthAccounts
from utils.consts import EnvName
from utils.error_log import error_log
from utils.faucet import Faucet
from utils.k6_helpers import k6_prepare_accounts, k6_set_envs, deploy_erc20_contract, deploy_block_number_contract
from utils.web3client import NeonChainWeb3Client

ERR_MESSAGES = {
    "run": "Unsuccessful tests executing",
    "requirements": "Unsuccessful requirements installation",
}


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
                add_error_log_comment(func.__name__, error)
                raise error

    return wrap


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
    default=EnvName.LOCAL,
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


@click.group()
def cli():
    pass


@cli.group()
@click.pass_context
def k6(ctx):
    """Commands for k6 load tests."""


@k6.command("build", help="Build k6 executable file.")
@click.option("-t", "--tag", default="05e0ce5", help="Eth plugin tag or commit sha to use")
@catch_traceback
def build(tag):
    xk6_install = "go install go.k6.io/xk6/cmd/xk6@latest"
    xk6_build = f"xk6 build --with github.com/szkiba/xk6-prometheus --with github.com/neonlabsorg/xk6-ethereum@{tag}"

    command_install = subprocess.run(xk6_install, shell=True)

    if command_install.returncode != 0:
        sys.exit(command_install.returncode)

    command_build = subprocess.run(xk6_build, shell=True)
    if command_build.returncode != 0:
        sys.exit(command_build.returncode)


@k6.command("run", help="Run k6 performance test.")
@click.option("-n", "--network", required=True, default="local", help="Which network to use for envs assignment")
@click.option(
    "-s", "--script", required=True, default="./loadtesting/k6/tests/sendNeon.test.js", help="Path to k6 script"
)
@click.option(
    "-u", "--users", default=None, required=True, help="Number of users (have to be generated before load test run)"
)
@click.option("-b", "--balance", default=None, required=True, help="Initial balance of accounts in Neon")
@click.option("-a", "--bank_account", default=None, required=False, help="Eth bank account private key")
@catch_traceback
def run_load_k6(network, script, users, balance, bank_account):
    network_manager = NetworkManager()
    network_object = network_manager.get_network_object(network)
    web3_client = NeonChainWeb3Client(proxy_url=network_object["proxy_url"])
    faucet = Faucet(faucet_url=network_object["faucet_url"], web3_client=web3_client)
    account_manager = EthAccounts(web3_client, faucet, bank_account)

    print("Compiling ERC20 contract...")
    command_erc20 = "solc --abi ./contracts/EIPs/ERC20/ERC20.sol -o ./loadtesting/k6/contracts/ERC20 --overwrite"
    command_erc20_run = subprocess.run(command_erc20, shell=True)
    if command_erc20_run.returncode != 0:
        sys.exit(command_erc20_run.returncode)

    print("Deploying ERC20 contract...")
    erc20 = deploy_erc20_contract(web3_client, faucet, account_manager.create_account(balance=int(balance)))
    print(f"ERC20 contract deployed at {erc20.contract.address} with owner {erc20.owner.address}")

    block_contract = deploy_block_number_contract(account_manager)

    k6_prepare_accounts(erc20, account_manager, users, balance, 100)
    k6_set_envs(network, erc20, users, balance, bank_account)
    os.environ["K6_BLOCK_ADDRESS"] = block_contract.address

    command = f"./k6 run {script} -o 'prometheus=namespace=k6'"
    command_run = subprocess.run(command, shell=True)
    if command_run.returncode != 0:
        sys.exit(command_run.returncode)


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
def run_load(credentials, host, users, spawn_rate, run_time, tag, web_ui, locustfile, neon_rpc):
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
        command += " --headless"

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
        command += " --run-time=120"
    if tag:
        command += f" --tags {' '.join(tag)}"
    else:
        command += " --tags prepare"

    cmd = subprocess.run(command, shell=True)

    if cmd.returncode != 0:
        sys.exit(cmd.returncode)


if __name__ == "__main__":
    cli()
