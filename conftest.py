# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""

import pytest

pytest_plugins = ["ui.plugins.browser"]


def pytest_addoption(parser):
    parser.addoption("--make-report", action="store_true", default=False, help="Store tests result to file")
