# coding: utf-8
"""
Created on 2021-10-01
@author: Eugeny Kurkovich
"""

import pathlib
import typing as tp
from dataclasses import dataclass

import pytest
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType

from ui import libs
from ui.pages import metamask, neon_faucet
from ui.plugins import browser

NEON_FAUCET_URL = "https://neonfaucet.org/"
"""Neon Test Airdrops
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
def required_extensions() -> tp.List:
    return "metamask"


@pytest.fixture
def context(
    browser_type: BrowserType,
    browser_context_args: tp.Dict,
    browser_type_launch_args: tp.Dict,
    chrome_extensions_path: pathlib.Path,
    chrome_extension_user_data: pathlib.Path,
) -> BrowserContext:
    """Override default context for MetaMasks load"""
    context = browser.create_persistent_context(
        browser_type,
        browser_context_args,
        browser_type_launch_args,
        ext_source=chrome_extensions_path,
        user_data_dir=chrome_extension_user_data.as_posix(),
    )
    yield context
    context.close()


class TestMetaMaskPipeLIne:
    """Tests NeonEVM proxy functionality via MetaMask"""

    @pytest.fixture
    def metamask_page(self, page, network: str, chrome_extension_password):
        login_page = metamask.MetaMaskLoginPage(page)
        mm_page = login_page.login(password=chrome_extension_password)
        mm_page.check_funds_protection()
        mm_page.change_network(network)
        mm_page.switch_assets()
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
        balance_before_airdrop_test = int(getattr(metamask_page, f"active_account_{tokens.lower()}_balance"))
        neon_faucet_page.connect_wallet()
        neon_faucet_page.send_tokens(tokens, 100)
        # wait new balance
        libs.try_until(
            lambda: balance_before_airdrop_test + 100
            == int(getattr(metamask_page, f"active_account_{tokens.lower()}_balance")),
            timeout=90,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=90, interval=5)
