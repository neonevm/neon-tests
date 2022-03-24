#!/usr/bin/env python3
import json
import sys
import click
import subprocess
import pathlib

networks = []
with open("./envs.json", "r") as f:
    networks = json.load(f).keys()


@click.group()
def cli():
    pass


@cli.command(help="Update base python requirements")
@click.option("--dev", help="Install development requirements", default=False, is_flag=True)
def requirements(dev=False):
    command = "pip3 install --upgrade -r deploy/requirements/prod.txt"
    if dev:
        command += " -r requirements-dev.txt"
    subprocess.check_call(command, shell=True)
    subprocess.check_call("pip3 install --no-deps -r deploy/requirements/nodeps.txt", shell=True)


@cli.command(help="Run any type of tests")
@click.option("-n", "--network", default="night-stand", type=click.Choice(networks), help="In which stand run tests")
@click.argument("name", required=True, type=click.Choice(["economy", "basic"]))
def run(name, network):
    command = ""
    if name == "economy":
        command = "py.test integration/tests/economy/test_economics.py"
    elif name == "basic":
        command = "py.test integration/tests/basic/"
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
    "--web-ui/--headless",
    " /-w",
    default=True,
    help="Enable the web interface. " "If UI is enabled, go to http://0.0.0.0:8089/ [default: `Web UI is enabled`]",
)
def locust(locustfile, credentials, host, users, spawn_rate, run_time, web_ui):
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
    if not web_ui:
        command += f" --headless"

    cmd = subprocess.run(command, shell=True)

    if cmd.returncode != 0:
        sys.exit(cmd.returncode)


if __name__ == "__main__":
    cli()
