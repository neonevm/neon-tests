# coding: utf-8
"""
Created on 2021-10-01
@author: Eugeny Kurkovich
"""

from dataclasses import dataclass
from urllib.parse import urlparse

import pytest
from playwright.sync_api import BrowserContext

from ui import libs
from ui.pages import metamask, neon_faucet
from utils.helpers import wait_condition

NEON_FAUCET_URL = "https://neonfaucet.org/"
DOCS_URL = "https://neonevm.org/docs/developing/utilities/faucet"
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


def get_metamask_extension_id(context: BrowserContext) -> str:
    for page in context.background_pages:
        url = page.url
        if url.startswith("chrome-extension://"):
            parsed_url = urlparse(url)
            extension_id = parsed_url.netloc
            return extension_id

    raise Exception("MetaMask extension ID not found.")


class TestFaucet:
    def test_click_help_button(self, context):
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        neon_faucet_page = neon_faucet.NeonTestAirdropsPage(page)
        with context.expect_page() as new_tab_info:
            neon_faucet_page.help_button_click()
        help_page = new_tab_info.value
        help_page.wait_for_load_state()
        assert DOCS_URL in help_page.url


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
        neon_faucet_page.connect_wallet()
        neon_faucet_page.send_tokens(tokens, 10)
        # wait new balance
        wait_condition(
            lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > balance_before_airdrop_test,
            timeout_sec=120,
            delay=2,
        )
        libs.try_until(
            lambda: balance_before_airdrop_test + 10 == int(getattr(metamask_page, f"{tokens.lower()}_balance")),
            timeout=90,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=90, interval=5)
