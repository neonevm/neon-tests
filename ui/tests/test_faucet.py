"""
Created on 2021-10-01
@author: Eugeny Kurkovich
"""

import random
from dataclasses import dataclass
from urllib.parse import urlparse

import pytest
from playwright.sync_api import BrowserContext
from playwright.sync_api import TimeoutError

from ui import libs
from ui.pages import metamask, neon_faucet
from ui.pages.navigation_target import NavigationTarget
from ui.pages.constants import NEON_FAUCET_URL
from ui.pages.neon_faucet import NeonTestAirdropsPage
from utils.helpers import wait_condition

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

token_random_amount = random.randint(1, 100)


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

    @pytest.mark.parametrize(
        "target",
        [
            NavigationTarget.FAQ,
            NavigationTarget.DOCS,
            NavigationTarget.ABOUT_NEON,
            NavigationTarget.TWITTER,
            NavigationTarget.DISCORD,
            NavigationTarget.SUPPORT,
            NavigationTarget.NEONPASS,
            NavigationTarget.COOKIES,
        ],
        ids=lambda t: t.test_name,
    )
    def test_navigation_targets(self, target: NavigationTarget, context: BrowserContext):
        page = context.new_page()
        page.goto(NEON_FAUCET_URL)
        neon = NeonTestAirdropsPage(page)
        neon.menu_dropdown_click()

        if target.opens_new_tab:
            with context.expect_page() as popup_info:
                getattr(neon, target.method_name)()
            new_page = popup_info.value
            new_page.wait_for_load_state()
            actual_url = new_page.url
        else:
            getattr(neon, target.method_name)()
            page.wait_for_url(f"**{target.expected_url}")
            actual_url = page.url

        assert target.expected_url in actual_url, (
            f"{target.description!r} should open '{target.expected_url}', " f"but actually opened '{actual_url}'"
        )


@pytest.mark.flaky(retries=3, retry_delay=2)
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
        neon_faucet_page.connect_wallet_to_faucet()
        metamask_page.set_metamask()
        neon_faucet_page.page.bring_to_front()
        neon_faucet_page.send_tokens(tokens, token_random_amount)
        neon_faucet_page.click_transfer_btn()
        neon_faucet_page.check_sucessfull_sent()
        wait_condition(
            lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > balance_before_airdrop_test,
            timeout_sec=240,
            delay=2,
        )
        libs.try_until(
            lambda: balance_before_airdrop_test + token_random_amount
            == int(getattr(metamask_page, f"{tokens.lower()}_balance")),
            timeout=240,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=240, interval=5)

    @pytest.mark.parametrize("tokens", [libs.Tokens.wneon.name])
    def test_get_spl_token_from_faucet(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neon_faucet_page: neon_faucet.NeonTestAirdropsPage,
        tokens: str,
    ) -> None:
        """Checks Neon faucet pipeline"""
        wait_condition(lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > 0, timeout_sec=240, delay=2)
        balance_before_airdrop_test = int(getattr(metamask_page, f"{tokens.lower()}_balance"))
        neon_faucet_page.connect_wallet_to_faucet()
        metamask_page.set_metamask()
        neon_faucet_page.page.bring_to_front()
        neon_faucet_page.send_tokens("Wrapped Neon", token_random_amount)
        neon_faucet_page.click_transfer_btn()
        neon_faucet_page.check_sucessfull_sent()
        # wait new balance
        wait_condition(
            lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > balance_before_airdrop_test,
            timeout_sec=360,
            delay=2,
        )
        libs.try_until(
            lambda: balance_before_airdrop_test + token_random_amount
            == int(getattr(metamask_page, f"{tokens.lower()}_balance")),
            timeout=360,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=360, interval=5)

    @pytest.mark.parametrize("tokens", [libs.Tokens.neon.name])
    def test_101_token_request(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neon_faucet_page: neon_faucet.NeonTestAirdropsPage,
        tokens: str,
    ) -> None:
        """Checks Neon faucet pipeline"""
        neon_faucet_page.connect_wallet_to_faucet()
        metamask_page.set_metamask()
        neon_faucet_page.page.bring_to_front()
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
        neon_faucet_page.connect_wallet_to_faucet()
        metamask_page.set_metamask()
        neon_faucet_page.page.bring_to_front()
        neon_faucet_page.send_tokens(tokens, token_random_amount)
        neon_faucet_page.click_transfer_btn()
        neon_faucet_page.check_sucessfull_sent()
        # wait new balance
        wait_condition(
            lambda: int(getattr(metamask_page, f"{tokens.lower()}_balance")) > balance_before_airdrop_test,
            timeout_sec=240,
            delay=2,
        )
        libs.try_until(
            lambda: balance_before_airdrop_test + token_random_amount
            == int(getattr(metamask_page, f"{tokens.lower()}_balance")),
            timeout=240,
            interval=5,
            error_msg=f"{tokens} balance was not changed after airdrop",
        )
        # Wait next airdrop was enabled
        libs.try_until(lambda: neon_faucet_page.is_airdrop_enabled, timeout=240, interval=5)

    @pytest.mark.skip
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
            neon_faucet_page.connect_wallet_to_faucet()
            metamask_page.set_metamask()
            neon_faucet_page.page.bring_to_front()
            neon_faucet_page.send_tokens("Wrapped Neon", token_random_amount)
            neon_faucet_page.click_transfer_btn()
            neon_faucet_page.check_sucessfull_sent()

            try:
                neon_faucet_page.wait_for_too_many_requests_notification(timeout=3000)
                return
            except TimeoutError:
                if attempt < MAX_RETRIES:
                    print(f"Attempt {attempt} failed — retrying...")
                else:
                    assert False, "Notification 'Too Many Requests' is not visible"
