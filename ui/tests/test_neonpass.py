import pathlib
import typing as tp
import uuid
from dataclasses import dataclass

import allure
import pytest
import requests
from _pytest.fixtures import FixtureRequest
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType

from ui import libs
from ui.libs import Platform, open_safe, Token, Tokens, FeeType
from ui.pages import metamask, neonpass
from ui.plugins import browser


@dataclass
class Wallet:
    name: str
    address: str = None


@dataclass
class Wallets:
    """Phantom used wallets"""

    wall_1 = Wallet("Wallet 1", "B4t7nCPsqKm38SZfV6k3pfrY7moQqYy7EBeMc7LgwYQ8")
    wall_2 = Wallet("Wallet 2")
    wall_3 = Wallet("Wallet 3")
    mm_wall_1 = Wallet("MM Wallet 1", "0x4701D3F6B2407911AFDf90c20537bD0c27214c9A")


@pytest.fixture(scope="session")
def required_extensions() -> tp.List:
    return ["metamask", "phantom"]


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


@pytest.fixture
def request_sol(solana_url: str) -> None:
    """Airdrop SOL"""
    json_doc = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "requestAirdrop",
        "params": [Wallets.wall_1.address, 1000000000],
    }
    response = requests.Session().post(url=solana_url, json=json_doc)
    assert response.ok


@allure.feature("UI")
@allure.story("NeonPass")
class TestNeonPass:
    """Tests NeonPass functionality"""

    @staticmethod
    def check_balance(
        init_balance: float,
        page: metamask.MetaMaskAccountsPage,
        platform: str,
        token: str,
    ) -> bool:
        """Compare balance"""
        balance = float(getattr(page, f"{token.name.lower()}_balance"))
        if platform == Platform.neon:
            return init_balance > balance
        elif platform == Platform.solana:
            return init_balance < balance

    @pytest.fixture
    def metamask_page(
        self, request: FixtureRequest, page, network: str, chrome_extension_password
    ):
        login_page = metamask.MetaMaskLoginPage(page)
        mm_page = login_page.login(password=chrome_extension_password)
        mm_page.check_funds_protection()
        mm_page.change_network(network)
        mm_page.switch_assets()
        yield mm_page
        mm_page.page.close()

    @pytest.fixture
    def neonpass_page(
        self, request: FixtureRequest, context: BrowserContext, neonpass_url: str
    ) -> neonpass.NeonPassPage:
        page = open_safe(context, neonpass_url)
        neon_page = neonpass.NeonPassPage(page)
        yield neon_page
        neon_page.page.close()

    @pytest.mark.parametrize(
        "platform, token, fee_type",
        [
            (Platform.solana, Tokens.neon, FeeType.neon),
            (Platform.solana, Tokens.neon, FeeType.sol),
            (Platform.solana, Tokens.sol, FeeType.none),
            (Platform.solana, Tokens.usdt, FeeType.none),
            (Platform.solana, Tokens.usdc, FeeType.none),
            (Platform.neon, Tokens.neon, FeeType.none),
            (Platform.neon, Tokens.wsol, FeeType.none),
            (Platform.neon, Tokens.usdt, FeeType.none),
            (Platform.neon, Tokens.usdc, FeeType.none),
        ],
        ids=str,
    )
    def test_send_tokens(
        self,
        metamask_page: metamask.MetaMaskAccountsPage,
        neonpass_page: neonpass.NeonPassPage,
        platform: str,
        token: Token,
        fee_type: str,
    ) -> None:
        """Prepare test environment"""

        def get_balance() -> float:
            return float(getattr(metamask_page, f"{token.name.lower()}_balance"))

        with allure.step("Get initial balance in the wallet"):
            init_balance = get_balance()

        with allure.step(f"On the Neonpass page connect wallets and transfer {token.name} from {platform}"):
            neonpass_page.connect_phantom()
            neonpass_page.connect_metamask()
            neonpass_page.switch_platform_source(platform)
            neonpass_page.set_source_token(token.name, 0.001)
            neonpass_page.set_transaction_fee(platform, token.name, fee_type)
            neonpass_page.confirm_tokens_transfer(platform, token)

        with allure.step("Making sure that the balance in the wallet changed"):
            metamask_page.page.bring_to_front()
            # check balance
            libs.try_until(
                lambda: init_balance < get_balance()
                if platform == Platform.solana
                else init_balance > get_balance(),
                timeout=60,
                interval=5,
                error_msg=f"{token.name} balance was not changed after tokens transfer",
        )
