# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""

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
    operator_keys: tp.List[str]


def pytest_addoption(parser):
    parser.addoption("--make-report", action="store_true", default=False, help="Store tests result to file")
    parser.addoption("--envs", action="store", default="envs.json", help="Filename with environments")


def pytest_sessionstart(session):
    """Hook for clearing the error log used by the slack notifications utility"""
    path = pathlib.Path(f"{clickfile.CMD_ERROR_LOG}")
    if path.exists():
        path.unlink()


def pytest_runtest_protocol(item, nextitem):
    if item.config.getoption("--make-report"):
        path = pathlib.Path(f"{clickfile.CMD_ERROR_LOG}")
        reports = runtestprotocol(item, nextitem=nextitem)
        with path.open("a") as fd:
            for report in reports:
                if report.when == "call" and report.outcome == "failed":
                    fd.write(f"`{report.outcome.upper()}` {item.nodeid}\n")
        return True


def pytest_configure(config: Config):
    network_name = config.getoption("--network", default="night-stand")
    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)
    assert network_name in environments, f"Environment {network_name} doesn't exist in envs.json"
    config.environment = EnvironmentConfig(**environments[network_name])
