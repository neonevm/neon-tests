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

from ui.pages import metamask, neonpass
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
        mm_page.switch_assets()

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
        request_sol: requests.Response,
        metamask_page: tp.Any,
        neonpass_page: neonpass.NeonPassPage,
        evm: str,
        tokens: str,
    ) -> None:
        """Prepare test environment"""
        neonpass_page.change_transfer_source(evm)
        neonpass_page.connect_wallet()
        neonpass_page.set_source_token(tokens, 1)
        neonpass_page.next_tab()
        neonpass_page.connect_wallet()
        neonpass_page.next_tab()
        neonpass_page.confirm_tokens_transfer()
