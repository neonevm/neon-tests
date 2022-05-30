# coding: utf-8
"""
Created on 2021-10-01
@author: Eugeny Kurkovich
"""

import os
import pathlib
import time
import typing as tp
from dataclasses import dataclass

import pytest
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType

from ui import libs
from ui.pages import metamask, neon_faucet
from ui.plugins import browser

try:
    METAMASK_PASSWORD = os.environ["METAMASK_PASSWORD"]
except KeyError:
    raise AssertionError("Please set the `METAMASK_PASSWORD` environment variable to connect to the wallet.")
# "1234Neon5678"


METAMASK_EXT_DIR = "extensions/chrome/metamask"
"""Relative path to MetaMask extension source
"""


NEON_FAUCET_URL = "https://neonfaucet.org/"
"""Neon Test Airdrops
"""

NEON_DEV_NET = "NeonEVM DevNet"
"""Development stend name
"""

BASE_NEON_BALANCE = 7000
"""Balance saved in MetaMask extension by default
"""


@dataclass
class Accounts:
    """MetaMask used accounts"""

    acc_1 = "Account 1"
    acc_2 = "Account 2"
    acc_3 = "Account 3"


@pytest.fixture(scope="session")
def metamask_dir(chrome_extension_base_path) -> pathlib.Path:
    """Path to MetaMask extension source"""
    return chrome_extension_base_path / METAMASK_EXT_DIR


@pytest.fixture(scope="session")
def metamask_user_data(metamask_dir: pathlib.Path) -> pathlib.Path:
    """Path to MetaMask extension user data"""
    #user_data = libs.clone_user_data(metamask_dir)
    #yield user_data
    #libs.rm_tree(user_data)
    user_dat = metamask_dir / 'user_data'
    print(f"{30*'!'}{user_dat}")
    return user_dat


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
        user_data_dir=metamask_user_data.as_posix(),
    )
    yield context
    context.close()


class TestMetaMaskPipeLIne:
    """Tests NeonEVM proxy functionality via MetaMask"""

    @pytest.fixture
    def metamask_page(self, page, network: str):
        time.sleep(7200)
        login_page = metamask.MetaMaskLoginPage(page)
        mm_page = login_page.login(password=METAMASK_PASSWORD)
        mm_page.check_funds_protection()
        mm_page.change_network(network)
        # wait MetaMask initialization
        libs.try_until(
            lambda: int(mm_page.active_account_neon_balance) != BASE_NEON_BALANCE,
            times=5,
            interval=2,
            raise_on_timeout=False,
        )
        return mm_page

    @pytest.fixture
    def neon_faucet_page(self, context: BrowserContext) -> neon_faucet.NeonTestAirdropsPage:
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        yield neon_faucet.NeonTestAirdropsPage(page)
        page.close()

    @pytest.mark.parametrize(
        "tokens",
        [libs.Tokens.neon, libs.Tokens.usdt],
    )
    def test_get_tokens_from_faucet(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neon_faucet_page: neon_faucet.NeonTestAirdropsPage,
        tokens: str,
    ) -> None:
        """Checks Neon faucet pipeline"""
        time.sleep(60)
        return
        balance_before_airdrop_test = int(getattr(metamask_page, f"active_account_{tokens.lower()}_balance"))
        neon_faucet_page.connect_wallet()
        neon_faucet_page.test_airdrop(tokens, 100)
        libs.try_until(
            lambda: balance_before_airdrop_test + 100
            == int(getattr(metamask_page, f"active_account_{tokens.lower()}_balance")),
            timeout=90,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=90, interval=5)
