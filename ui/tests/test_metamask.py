# coding: utf-8
"""
Created on 2021-10-01
@author: Eugeny Kurkovich
"""

import os
import pathlib
import shutil
import time
import typing as tp
import uuid

import pytest
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType

from ui.pages import metamask, neon_faucet
from ui.plugins import browser

BASE_USER_DATA_DIR = "user_data"
"""Path to a User Data Directory, which stores browser session data like cookies and local storage.
"""

METAMASK_EXT_DIR = "extensions/chrome/metamask"
"""Relative path to MetaMask extension source
"""
try:
    METAMASK_PASSWORD = os.environ["METAMASK_PASSWORD"]
except KeyError:
    raise AssertionError("Please set the `METAMASK_PASSWORD` environment variable to connect to the wallet.")
# "1234Neon5678"


NEON_FAUCET_URL = "https://neonfaucet.org/"
"""Neon Test Airdrops
"""

NEON_DEV_NET = "NeonEVM DevNet"
"""Development stend name
"""


@pytest.fixture(scope="session")
def metamask_dir(chrome_extension_base_path) -> pathlib.Path:
    """Path to MetaMask extension source"""
    return chrome_extension_base_path / METAMASK_EXT_DIR


@pytest.fixture(scope="session")
def metamask_user_data(metamask_dir: pathlib.Path) -> pathlib.Path:
    """Path to MetaMask extension user data"""

    def rm_tree(p: pathlib.Path) -> None:
        """Remove user data"""
        if p.is_file():
            p.unlink()
        else:
            for child in p.iterdir():
                rm_tree(child)
            p.rmdir()

    user_data = shutil.copytree(metamask_dir / BASE_USER_DATA_DIR, metamask_dir / uuid.uuid4().hex)
    yield user_data
    rm_tree(user_data)


@pytest.fixture(autouse=True)
def use_persistent_context() -> bool:
    """Flag used to load Chrome extensions overridden to load MetaMasks"""
    return True


@pytest.fixture
def context(
    browser_type: BrowserType,
    browser_context_args: tp.Dict,
    browser_type_launch_args: tp.Dict,
    metamask_dir: pathlib.Path,
    metamask_user_data: pathlib.Path,
) -> BrowserContext:
    """Override default context for MetaMasks load"""
    context = browser.create_persistent_context(
        browser_type,
        browser_context_args,
        browser_type_launch_args,
        ext_source=metamask_dir,
        user_data_dir=metamask_user_data,
    )
    yield context
    context.close()


class TestMetaMaskPipeLIne:
    """Tests NeonEVM proxy functionality via MetaMask"""

    @pytest.fixture
    def metamask_page(self, page):
        login_page = metamask.MetaMaskLoginPage(page)
        return login_page.login(password=METAMASK_PASSWORD)

    @pytest.fixture
    def neon_faucet_page(self, context: BrowserContext) -> neon_faucet.NeonTestAirdropsPage:
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        yield neon_faucet.NeonTestAirdropsPage(page)
        page.close()

    def test_connect_metamask_to_neon_faucet(
        self, metamask_page: metamask.MetaMaskAccountsPage, neon_faucet_page: neon_faucet.NeonTestAirdropsPage
    ) -> None:
        metamask_page.change_network(NEON_DEV_NET)
        neon_faucet_page.connect_wallet()
        time.sleep(10)
