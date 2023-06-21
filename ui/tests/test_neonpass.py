# coding: utf-8
"""
Created on 2022-06-16
@author: Eugeny Kurkovich
"""
import pathlib
import typing as tp
import uuid
from dataclasses import dataclass

import pytest
import requests
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType

from ui import libs
from ui.pages import metamask, neonpass
from ui.plugins import browser

NEON_PASS_URL = "http://devnet.neonpass.live"
"""tokens transfer service
"""

SOL_API_URL = "https://api.devnet.solana.com/"
"""Solana DevNet API url"""


@dataclass
class EVM:
    solana: str = "Solana"
    neon: str = "Neon"


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


@pytest.fixture
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
def request_sol() -> None:
    """Airdrop SOL"""
    json_doc = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "requestAirdrop",
        "params": [Wallets.wall_1.address, 1000000000],
    }
    response = requests.Session().post(url=SOL_API_URL, json=json_doc)
    print(response.json())
    assert response.ok


class TestPhantomPipeLIne:
    """Tests NeonPass functionality via Phantom"""

    @staticmethod
    def check_balance(init_balance: float, page: metamask.MetaMaskAccountsPage, evm: str, token: str) -> bool:
        """Compare balance"""
        balance = float(getattr(page, f"{token.name.lower()}_balance"))
        if evm == EVM.neon:
            return init_balance > balance
        elif evm == EVM.solana:
            return init_balance < balance

    @pytest.fixture
    def metamask_page(self, page, network: str, chrome_extension_password):
        login_page = metamask.MetaMaskLoginPage(page)
        mm_page = login_page.login(password=chrome_extension_password)
        mm_page.check_funds_protection()
        mm_page.change_network(network)
        mm_page.switch_assets()
        yield mm_page
        page.close()

    @pytest.fixture
    def neonpass_page(self, context: BrowserContext) -> neonpass.NeonPassPage:
        page = context.new_page()
        page.goto(NEON_PASS_URL)
        yield neonpass.NeonPassPage(page)
        page.close()

    @pytest.mark.parametrize(
        "evm, tokens",
        [
            (EVM.solana, libs.Tokens.neon),
            (EVM.solana, libs.Tokens.usdt),
            (EVM.neon, libs.Tokens.neon),
            (EVM.neon, libs.Tokens.usdt),
        ],
    )
    def test_send_tokens(
        self,
        # request_sol: requests.Response,
        metamask_page: metamask.MetaMaskAccountsPage,
        neonpass_page: neonpass.NeonPassPage,
        evm: str,
        tokens: str,
    ) -> None:
        """Prepare test environment"""
        def get_balance() -> float:
            return float(getattr(metamask_page, f"{tokens.name.lower()}_balance"))

        init_balance = get_balance()
        neonpass_page.connect_phantom()
        neonpass_page.connect_metamask()
        neonpass_page.set_source_token(tokens.name, 0.1)
        neonpass_page.confirm_tokens_transfer()
        metamask_page.page.bring_to_front()

        # check balance
        libs.try_until(
            lambda: init_balance < get_balance() if evm == EVM.solana else init_balance > get_balance(),
            timeout=60,
            interval=5,
            error_msg=f"{tokens.name} balance was not changed after tokens transfer",
        )
