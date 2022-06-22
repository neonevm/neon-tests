# coding: utf-8
"""
Created on 2022-06-16
@author: Eugeny Kurkovich
"""
import time
import pathlib
import typing as tp
import uuid
from dataclasses import dataclass

import pytest
import requests
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType

from ui.pages import metamask, phantom, neonpass
from ui.plugins import browser
from ui import libs


NEON_PASS_URL = "https://neonpass.live/"
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
def request_sol() -> None:
    """Airdrop SOL"""
    json_doc = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "requestAirdrop",
        "params": [Wallets.wall_1.address, 1000000000],
    }
    assert requests.Session().post(url=SOL_API_URL, json=json_doc).ok


class TestPhantomPipeLIne:
    """Tests NeonPass functionality via Phantom"""

    @pytest.fixture
    def metamask_page(self, page, network: str, chrome_extension_password):
        login_page = metamask.MetaMaskLoginPage(page)
        mm_page = login_page.login(password=chrome_extension_password)
        mm_page.check_funds_protection()
        mm_page.change_network(network)

    @pytest.fixture
    def phantom_page(self, page, network: str, chrome_extension_password: str):
        # login_page = phantom.PhantomLoginPage(page)
        # phantom_page = login_page.login(password=chrome_extension_password)
        # mm_page.check_funds_protection()
        # mm_page.change_network(network)
        # wait MetaMask initialization
        # libs.try_until(
        #    lambda: int(mm_page.active_account_neon_balance) != BASE_NEON_BALANCE,
        #    times=5,
        #    interval=2,
        #    raise_on_timeout=False,
        # )
        # return phantom_page
        pass

    @pytest.fixture
    def neon_pass_page(self, context: BrowserContext) -> neonpass.NeonPassPage:
        page = context.new_page()
        page.goto(NEON_PASS_URL)
        yield neonpass.NeonPassPage(page)
        page.close()

    @pytest.fixture
    def prepare_env(
        self, request_sol: requests.Response, metamask_page: tp.Any, neon_pass_page: neonpass.NeonPassPage
    ) -> None:
        """Prepare test environment"""
        neon_pass_page.change_transfer_source(EVM.neon)
        neon_pass_page.connect_source_wallet()
        neon_pass_page.set_source_token(libs.Tokens.neon, 10)
        neon_pass_page.connect_destination_wallet()

    def test_login(self, prepare_env) -> None:

        time.sleep(7200)
