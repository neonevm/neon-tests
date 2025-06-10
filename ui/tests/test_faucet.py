"""
Created on 2021-10-01
@author: Eugeny Kurkovich
"""

from dataclasses import dataclass
from urllib.parse import urlparse

import pytest
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType

from ui import libs
from ui.pages import metamask, neon_faucet
from utils.helpers import wait_condition

NEON_FAUCET_URL = "https://neonfaucet.org/"
DOCS_URL = "https://neonevm.org/docs/developing/utilities/faucet"
WEBSITE_URL = "https://www.neonevm.org/"
NEONPASS_URL = "https://neonpass.live/"

"""Neon Test Airdrops
"""

BASE_NEON_BALANCE = 7000
"""Balance saved in MetaMask extension by default
"""

MOBILE_VIEWPORT = {"width": 375, "height": 812}  # iPhone X, например
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 "
    "Mobile/15E1"
)


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
        actual_url = help_page.url
        assert DOCS_URL in actual_url, (
            f"Help button should open documentation at '{DOCS_URL}', " f"but actually opened '{actual_url}'"
        )

    def test_click_neon_website_button(self, context):
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        neon_faucet_page = neon_faucet.NeonTestAirdropsPage(page)
        with context.expect_page() as new_tab_info:
            neon_faucet_page.neon_website_button_click()
        neon_website_page = new_tab_info.value
        neon_website_page.wait_for_load_state()
        actual_url = neon_website_page.url
        assert WEBSITE_URL in neon_website_page.url, (
            f"Neon Website button should open '{WEBSITE_URL}', " f"but actually opened '{actual_url}'"
        )

    def test_click_neonpass_button(self, context):
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        neon_faucet_page = neon_faucet.NeonTestAirdropsPage(page)
        with context.expect_page() as new_tab_info:
            neon_faucet_page.neonpass_button_click()
        neonpass_page = new_tab_info.value
        neonpass_page.wait_for_load_state()
        actual_url = neonpass_page.url
        assert NEONPASS_URL in neonpass_page.url, (
            f"NeonPass button should open '{NEONPASS_URL}', " f"but actually opened '{actual_url}'"
        )

    @pytest.mark.no_extension
    def test_open_faucet_without_installed_wallets(self, context):
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        neon_faucet_page = neon_faucet.NeonTestAirdropsPage(page)
        neon_faucet_page.install_wallet_message()

    def test_mobile_faucet_message(self, browser_type: BrowserType):
        expected_message = "Sorry, Neon Faucet "
        context = browser_type.launch_persistent_context(
            user_data_dir="/tmp/mobile-user-data",
            viewport=MOBILE_VIEWPORT,
            user_agent=MOBILE_USER_AGENT,
            is_mobile=True,
            device_scale_factor=2,
            has_touch=True,
            headless=False,
        )
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        content = page.content()

        assert "Sorry, Neon Faucet " in page.content()

        assert expected_message in content, f"Expected '{expected_message}' in page content, but it was not found."
        context.close()


@pytest.mark.flaky(retries=3, retriy_delay=2)
class TestMetaMaskPipeLIne:
    """Tests NeonEVM proxy functionality via MetaMask"""

    @pytest.fixture
    def neon_faucet_page(self, context: BrowserContext) -> neon_faucet.NeonTestAirdropsPage:
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        yield neon_faucet.NeonTestAirdropsPage(page)
        page.close()

    @pytest.mark.parametrize("tokens", [libs.Tokens.neon.name])
    def test_get_neon_tokens_from_faucet(
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
        neon_faucet_page.click_transfer_btn()
        neon_faucet_page.check_sucessfull_sent()
        # wait new balance
        wait_condition(
            lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > balance_before_airdrop_test,
            timeout_sec=240,
            delay=2,
        )
        libs.try_until(
            lambda: balance_before_airdrop_test + 10 == int(getattr(metamask_page, f"{tokens.lower()}_balance")),
            timeout=240,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=240, interval=5)

    @pytest.mark.parametrize("tokens", [libs.Tokens.neon.name])
    def test_search_not_existing_token(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neon_faucet_page: neon_faucet.NeonTestAirdropsPage,
        tokens: str,
    ) -> None:
        """Checks Neon faucet pipeline"""
        wait_condition(lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > 0, timeout_sec=120, delay=2)
        neon_faucet_page.connect_wallet()
        neon_faucet_page.choose_non_existing_token("BTC")

    @pytest.mark.parametrize("tokens", [libs.Tokens.wneon.name])
    def test_get_spl_token_from_faucet(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neon_faucet_page: neon_faucet.NeonTestAirdropsPage,
        tokens: str,
    ) -> None:
        """Checks Neon faucet pipeline"""
        wait_condition(lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > 0, timeout_sec=120, delay=2)
        balance_before_airdrop_test = int(getattr(metamask_page, f"{tokens.lower()}_balance"))
        neon_faucet_page.connect_wallet()
        neon_faucet_page.send_tokens("wNEON", 3)
        neon_faucet_page.click_transfer_btn()
        neon_faucet_page.check_sucessfull_sent()
        # wait new balance
        wait_condition(
            lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > balance_before_airdrop_test,
            timeout_sec=240,
            delay=2,
        )
        libs.try_until(
            lambda: balance_before_airdrop_test + 3 == int(getattr(metamask_page, f"{tokens.lower()}_balance")),
            timeout=240,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=240, interval=5)

    @pytest.mark.parametrize("tokens", [libs.Tokens.neon.name])
    def test_101_token_request(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neon_faucet_page: neon_faucet.NeonTestAirdropsPage,
        tokens: str,
    ) -> None:
        """Checks Neon faucet pipeline"""
        neon_faucet_page.connect_wallet()
        neon_faucet_page.text_too_much_tokens(tokens, 101)

    @pytest.mark.parametrize("tokens", [libs.Tokens.usdt.name])
    def test_get_usdt_tokens_from_faucet(
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
        neon_faucet_page.click_transfer_btn()
        neon_faucet_page.check_sucessfull_sent()
        # wait new balance
        wait_condition(
            lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > balance_before_airdrop_test,
            timeout_sec=240,
            delay=2,
        )
        libs.try_until(
            lambda: balance_before_airdrop_test + 10 == int(getattr(metamask_page, f"{tokens.lower()}_balance")),
            timeout=240,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=240, interval=5)

    @pytest.mark.parametrize("tokens", [libs.Tokens.neon.name])
    def test_get_1_token_per_10_seconds(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neon_faucet_page: neon_faucet.NeonTestAirdropsPage,
        tokens: str,
    ) -> None:
        MAX_RETRIES = 3
        """Checks Neon faucet pipeline"""
        for attempt in range(1, MAX_RETRIES + 1):
            neon_faucet_page.reload_page()
            neon_faucet_page.connect_wallet()
            neon_faucet_page.send_tokens(tokens, 3)
            neon_faucet_page.click_transfer_btn()

            try:
                neon_faucet_page.wait_for_too_many_requests_notification(timeout=3000)
                return
            except TimeoutError:
                if attempt < MAX_RETRIES:
                    print(f"Attempt {attempt} failed — retrying...")
                else:
                    assert False, "Notification 'Too Many Requests' is not visible"
