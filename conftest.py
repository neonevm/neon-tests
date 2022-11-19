import os
import json
import pathlib
import typing as tp
from dataclasses import dataclass

from _pytest.config import Config
from _pytest.runner import runtestprotocol

import clickfile

pytest_plugins = ["ui.plugins.browser"]


@dataclass
class EnvironmentConfig:
    evm_loader: str
    proxy_url: str
    solana_url: str
    faucet_url: str
    network_id: int
    operator_neon_rewards_address: tp.List[str]
    spl_neon_mint: str
    neon_erc20wrapper_address: str
    account_seed_version: str
    operator_keys: tp.List[str]


def pytest_addoption(parser):
    parser.addoption("--network", action="store", default="night-stand", help="Which stand use")
    parser.addoption("--make-report", action="store_true", default=False, help="Store tests result to file")
    parser.addoption("--envs", action="store", default="envs.json", help="Filename with environments")


def pytest_sessionstart(session):
    """Hook for clearing the error log used by the slack notifications utility"""
    path = pathlib.Path(f"{clickfile.CMD_ERROR_LOG}")
    if path.exists():
        path.unlink()


def pytest_runtest_protocol(item, nextitem):
    ihook = item.ihook
    ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
    reports = runtestprotocol(item, nextitem=nextitem)
    ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)
    if item.config.getoption("--make-report"):
        path = pathlib.Path(f"{clickfile.CMD_ERROR_LOG}")
        with path.open("a") as fd:
            for report in reports:
                if report.when == "call" and report.outcome == "failed":
                    fd.write(f"`{report.outcome.upper()}` {item.nodeid}\n")
    return True


def pytest_configure(config: Config):
    network_name = config.getoption("--network")
    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)
    assert network_name in environments, f"Environment {network_name} doesn't exist in envs.json"
    env = environments[network_name]
    if network_name == "devnet":
        if "SOLANA_URL" in os.environ:
            env["solana_url"] = os.environ.get("SOLANA_URL")
        if "PROXY_URL" in os.environ:
            env["proxy_url"] = os.environ.get("PROXY_URL")
    config.environment = EnvironmentConfig(**env)
