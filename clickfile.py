#!/usr/bin/env python3
import json
import sys
import click
import subprocess

networks = []
with open('./envs.json', 'r') as f:
    networks = json.load(f).keys()


@click.group()
def cli():
    pass


@cli.command(help="Update base python requirements")
@click.option('--dev', help="Install development requirements", default=False, is_flag=True)
def requirements(dev=False):
    command = 'pip3 install --upgrade -r deploy/requirements/prod.txt'
    if dev:
        command += ' -r requirements-dev.txt'
    subprocess.check_call(command, shell=True)
    subprocess.check_call('pip3 install --no-deps -r deploy/requirements/nodeps.txt', shell=True)


@cli.command(help="Run any type of tests")
@click.option('-n', '--network', default="night-stand", type=click.Choice(networks), help="In which stand run tests")
@click.argument('name', required=True, type=click.Choice(["economy", "basic"]))
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


if __name__ == "__main__":
    cli()
