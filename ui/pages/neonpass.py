# coding: utf-8
"""
Created on 2022-06-16
@author: Eugeny Kurkovich
"""

import os

from playwright._impl._api_types import TimeoutError

from ui import components, libs
from ui.pages import phantom, metamask
from . import BasePage
from ..libs import Platform


class NeonPassPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(NeonPassPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("button.wallet-button")

    @staticmethod
    def _handle_phantom_unlock(page) -> None:
        page.wait_for_load_state()
        phantom_page = phantom.PhantomUnlockPage(page)
        phantom_page.page_loaded()
        phantom_page.unlock(os.environ.get("CHROME_EXT_PASSWORD"))
        phantom_page.connect()

    @staticmethod
    def _handle_metamask_connect(page) -> None:
        mm_page = metamask.MetaMaskConnectPage(page)
        mm_page.next()
        mm_page.connect()

    @staticmethod
    def _handle_mm_withdraw_confirm(page) -> None:
        """MetaMask withdraw confirm"""
        page.wait_for_load_state()
        mm_confirm_page = metamask.MetaMaskWithdrawConfirmPage(page)
        mm_confirm_page.withdraw_confirm()

    @staticmethod
    def _handle_pt_withdraw_confirm(page) -> None:
        """Phantom withdraw confirm"""
        page.wait_for_load_state()
        phantom_confirm_page = phantom.PhantomWithdrawConfirmPage(page)
        phantom_confirm_page.withdraw_confirm()

    @property
    def _is_source_tab_loaded(self) -> bool:
        """Waiting for source tab"""
        try:
            return self.page.wait_for_selector(
                selector="//app-wallet-button[@label='From']//*[text()='Connect Wallet']", timeout=10000
            )
        except TimeoutError:
            return False

    @property
    def _is_target_tab_loaded(self) -> bool:
        """Waiting for target tab"""
        try:
            return self.page.wait_for_selector(
                selector="//app-wallet-button[@label='To']//*[text()='Connect Wallet']", timeout=10000
            )
        except TimeoutError:
            return False

    def switch_platform_source(self, platform: str) -> None:
        """Change transfer source platform (Neon/Solana)"""
        selector = f"//app-wallet-button[@label='From']//*[text()='{platform}']"  # desired platform

        if not self.page.query_selector(selector):  # if it's not already set -> switch
            components.Button(
                self.page,
                selector="//1button[@class='switch-button']",
            ).click()
            self.page.wait_for_selector(selector)

    def connect_phantom(self, timeout: float = 30000) -> None:
        """Connect Phantom Wallet"""
        # Wait page loaded
        if self._is_source_tab_loaded:
            pass
        try:
            with self.page.context.expect_page(timeout=timeout) as phantom_page_info:
                components.Button(
                    self.page, selector="//app-wallet-button[@label='From']//*[text()='Connect Wallet']").click()
            self._handle_phantom_unlock(phantom_page_info.value)
            self.page.wait_for_selector(
                selector="//app-wallet-button[@label='From']//*[contains(text(),'B4t7')]", timeout=timeout)
        except TimeoutError as e:
            if 'waiting for event "page"' not in e.message:
                raise e

    def connect_metamask(self, timeout: float = 30000) -> None:
        """Connect Metamask Wallet"""
        # Wait page loaded
        if self._is_target_tab_loaded:
            pass
        try:
            with self.page.context.expect_page(timeout=timeout) as mm_page_connect:
                components.Button(
                    self.page, selector="//app-wallet-button[@label='To']//*[text()='Connect Wallet']").click()
            self._handle_metamask_connect(mm_page_connect.value)
            self.page.wait_for_selector(
                selector="//app-wallet-button[@label='To']//*[contains(text(),'0x4701')]", timeout=timeout)
        except TimeoutError as e:
            if 'waiting for event "page"' not in e.message:
                raise e

    def set_source_token(self, token: str, amount: float) -> None:
        """Set source token and amount ti transfer"""
        components.Button(self.page, text="Select token").click()
        self.page.wait_for_selector(selector="//div[contains(@class, 'tokens-options')]")
        components.Button(self.page, selector=f"//button//*[text()='{token}']").click()
        self.page.wait_for_selector(selector="//label[contains(text(), 'balance')]")
        components.Input(self.page, selector="//input[contains(@class, 'token-amount-input')]").fill(str(amount))

    def next_tab(self) -> None:
        """Got to next tab"""
        button = self.page.wait_for_selector(selector="//div[contains(@class, 'button') and text()='Next']")
        button.click()

    def confirm_tokens_transfer(self, platform: str, token: str, timeout: float = 30000) -> None:
        """Confirm tokens withdraw"""
        with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
            self.page.wait_for_selector(selector="//button[contains(@class, 'transfer-button')]").click()
        confirm_page = confirm_page_info.value

        if platform == Platform.solana:
            if token in [libs.Tokens.sol]:
                with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
                    self._handle_pt_withdraw_confirm(confirm_page)
                confirm_page = confirm_page_info.value
            self._handle_pt_withdraw_confirm(confirm_page)

        if platform == Platform.neon:
            if token in [libs.Tokens.wsol]:
                with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
                    self._handle_pt_withdraw_confirm(confirm_page)
                confirm_page = confirm_page_info.value
                with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
                    self._handle_mm_withdraw_confirm(confirm_page)
                confirm_page = confirm_page_info.value
                self._handle_pt_withdraw_confirm(confirm_page)
            else:
                if token in [libs.Tokens.usdt, libs.Tokens.usdc]:
                    with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
                        self._handle_pt_withdraw_confirm(confirm_page)
                    confirm_page = confirm_page_info.value
                self._handle_mm_withdraw_confirm(confirm_page)

        # Close overlay message 'Transfer complete'
        self.page.wait_for_selector(selector="//*[text()='Transfer complete']")
        components.Button(self.page, selector="//*[text()='Close']").click()
        self._is_source_tab_loaded
