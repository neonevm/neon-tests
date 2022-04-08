#!/usr/bin/env python3
import os
import json
import sys
import click
import subprocess
import pathlib
from multiprocessing.dummy import Pool

try:
    from utils import web3client
    from utils import faucet
except ImportError:
    pass


networks = []
with open("./envs.json", "r") as f:
    networks = json.load(f)


def header(text):
    print(text.capitalize().center(80, "-"))


def prepare_wallets_with_balance(network, count=10, airdrop_amount=20000):
    header(f"Preparing {count} wallets with balances")
    settings = networks[network]
    web3_client = web3client.NeonWeb3Client(settings["proxy_url"], settings["network_id"])
    faucet_client = faucet.Faucet(settings["faucet_url"])
    private_keys = []

    for i in range(count):
        acc = web3_client.eth.account.create()
        faucet_client.request_neon(acc.address, airdrop_amount)
        if i in (0, 1, 2):
            faucet_client.request_neon(acc.address, airdrop_amount)
        private_keys.append(acc.privateKey.hex())
    return private_keys


def run_openzeppelin_tests(network, jobs=8):
    header(f"Running OpenZeppelin tests in {jobs} jobs on {network}")
    cwd = (pathlib.Path().parent / "compatibility/openzeppelin-contracts").absolute()
    subprocess.check_call("npx hardhat compile", shell=True, cwd=cwd)
    (cwd.parent / "results").mkdir(parents=True, exist_ok=True)
    keys_env = [prepare_wallets_with_balance(network) for i in range(jobs)]

    tests = subprocess.check_output("find \"test\" -name '*.test.js'", shell=True, cwd=cwd).decode().splitlines()

    def run_oz_file(file_name):
        header(f"Running {file_name}")
        keys = keys_env.pop(0)
        env = os.environ.copy()
        env["PRIVATE_KEYS"] = ",".join(keys)
        env["NETWORK_ID"] = str(networks[network]["network_id"])
        env["PROXY_URL"] = networks[network]["proxy_url"]
        
        out = subprocess.run(f"npx hardhat test {file_name}", shell=True, cwd=cwd, capture_output=True, env=env)
        stdout = out.stdout.decode()
        stderr = out.stderr.decode()
        print(stdout)
        print(stderr)
        keys_env.append(keys)
        log_dirs = (cwd.parent / "results" / file_name.replace(".", "_"))
        log_dirs.mkdir(parents=True, exist_ok=True)
        with open(log_dirs / "stdout.log", "w") as f:
            f.write(stdout)
        with open(log_dirs / "stderr.log", "w") as f:
            f.write(stderr)

    pool = Pool(jobs)
    pool.map(run_oz_file, tests)
    pool.close()
    pool.join()


def install_python_requirements():
    command = "pip3 install --upgrade -r deploy/requirements/prod.txt  -r deploy/requirements/devel.txt"
    subprocess.check_call(command, shell=True)
    subprocess.check_call("pip3 install --no-deps -r deploy/requirements/nodeps.txt", shell=True)


def install_oz_requirements():
    cwd = (pathlib.Path().parent / "compatibility/openzeppelin-contracts").absolute()
    subprocess.check_call("yarn install", shell=True, cwd=cwd)


@click.group()
def cli():
    pass


@cli.command(help="Update base python requirements")
def requirements():
    install_python_requirements()
    install_oz_requirements()


@cli.command(help="Run any type of tests")
@click.option("-n", "--network", default="n ight-stand", type=click.Choice(networks.keys()), help="In which stand run tests")
@click.option("-j", "--jobs", default=8, help="Number of parallel jobs (for openzeppelin)")
@click.argument("name", required=True, type=click.Choice(["economy", "basic", "oz"]))
def run(name, network, jobs):
    if name == "economy":
        command = "py.test integration/tests/economy/test_economics.py"
    elif name == "basic":
        command = "py.test integration/tests/basic/"
    elif name == "oz":
        run_openzeppelin_tests(network, jobs=int(jobs))
        return
    else:
        raise click.ClickException("Unknown test name")

    command += f" --network={network}"
    cmd = subprocess.run(command, shell=True)

    if cmd.returncode != 0:
        sys.exit(cmd.returncode)


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
    help="tag to include in the test, so only tasks "
         "with any matching tags will be executed"
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


if __name__ == "__main__":
    cli()
