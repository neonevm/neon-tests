# coding: utf-8
"""
Created on 2022-04-29
@author: Eugeny Kurkovich
"""
import pathlib
import pytest

import clickfile
from _pytest.runner import runtestprotocol


def pytest_addoption(parser):
    parser.addoption("--make-report", action="store_true", help="Store tests result to file")


def pytest_sessionstart(session):
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
