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
from utils.helpers import wait_condition

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


def get_metamask_extension_id(context: BrowserContext) -> str:
    extension_id = None
    for page in context.background_pages:
        url = page.url
        if url.startswith("chrome-extension://"):
            extension_id = url.split("/")[2]
            break
    if not extension_id:
        raise Exception("MetaMask extension ID not found.")
    return extension_id


@pytest.fixture
def metamask_page(
    context: BrowserContext,
    network: str,
    chrome_extension_password: str,
) -> metamask.MetaMaskAccountsPage:
    page = context.new_page()
    page.goto("about:blank")
    extension_id = get_metamask_extension_id(context)
    page.goto(f"chrome-extension://{extension_id}/home.html")

    login_page = metamask.MetaMaskLoginPage(page)
    popup_news = login_page.login(password=chrome_extension_password)
    mm_page = popup_news.close()
    mm_page.check_funds_protection()
    mm_page.change_network(network)
    mm_page.switch_assets()
    # wait MetaMask initialization
    libs.try_until(
        lambda: int(mm_page.neon_balance) != BASE_NEON_BALANCE,
        times=5,
        interval=2,
        raise_on_timeout=False,
    )

    return mm_page


class TestMetaMaskPipeLIne:
    """Tests NeonEVM proxy functionality via MetaMask"""

    @pytest.fixture
    def neon_faucet_page(self, context: BrowserContext) -> neon_faucet.NeonTestAirdropsPage:
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        yield neon_faucet.NeonTestAirdropsPage(page)
        page.close()

    @pytest.mark.parametrize("tokens", [libs.Tokens.neon.name, libs.Tokens.usdt.name])
    def test_get_tokens_from_faucet(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neon_faucet_page: neon_faucet.NeonTestAirdropsPage,
        tokens: str,
    ) -> None:
        """Checks Neon faucet pipeline"""
        wait_condition(lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > 0, timeout_sec=120, delay=2)
        balance_before_airdrop_test = int(getattr(metamask_page, f"{tokens.lower()}_balance"))
        print("Balance before airdrop", balance_before_airdrop_test)
        neon_faucet_page.connect_wallet()
        neon_faucet_page.send_tokens(tokens, 10)
        # wait new balance
        wait_condition(
            lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > balance_before_airdrop_test,
            timeout_sec=120,
            delay=2,
        )
        print("Balance after airdrop", int(getattr(metamask_page, f"{tokens.lower()}_balance")))
        libs.try_until(
            lambda: balance_before_airdrop_test + 10 == int(getattr(metamask_page, f"{tokens.lower()}_balance")),
            timeout=90,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=90, interval=5)
