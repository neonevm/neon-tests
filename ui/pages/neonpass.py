# coding: utf-8
"""
Created on 2022-06-16
@author: Eugeny Kurkovich
"""

import os

import allure
from playwright._impl._api_types import TimeoutError
from playwright.sync_api import expect

from ui import components, libs
from ui.pages import phantom, metamask
from . import BasePage
from ..libs import Platform, Token, Tokens


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
        with allure.step("MetaMask withdraw confirm"):
            page.wait_for_load_state()
            mm_confirm_page = metamask.MetaMaskWithdrawConfirmPage(page)
            mm_confirm_page.withdraw_confirm()

    @staticmethod
    def _handle_pt_withdraw_confirm(page) -> None:
        """Phantom withdraw confirm"""
        with allure.step("Phantom withdraw confirm"):
            page.wait_for_load_state()
            phantom_confirm_page = phantom.PhantomWithdrawConfirmPage(page)
            phantom_confirm_page.withdraw_confirm()

    @property
    def _is_source_tab_loaded(self) -> bool:
        """Waiting for source tab"""
        try:
            self.page.wait_for_selector(
                selector="//app-wallet-button[@label='From']//*[text()='Connect Wallet']", timeout=30000
            )
            return True
        except TimeoutError:
            return False

    @property
    def _is_target_tab_loaded(self) -> bool:
        """Waiting for target tab"""
        try:
            self.page.wait_for_selector(
                selector="//app-wallet-button[@label='To']//*[text()='Connect Wallet']", timeout=30000
            )
            return True
        except TimeoutError:
            return False

    @allure.step("Switch platform source to {platform}")
    def switch_platform_source(self, platform: str) -> None:
        """Change transfer source platform (Neon/Solana)"""
        selector = f"//app-wallet-button[@label='From']//*[text()='{platform}']"  # desired platform

        if not self.page.query_selector(selector):  # if it's not already set -> switch
            components.Button(
                self.page,
                selector="//button[@class='switch-button']",
            ).click()
            self.page.wait_for_selector(selector)

    @allure.step("Connect Phantom Wallet")
    def connect_phantom(self, timeout: float = 30000) -> None:
        """Connect Phantom Wallet"""
        # Wait page loaded
        if self._is_source_tab_loaded:
            pass
        try:
            with self.page.context.expect_page(timeout=timeout) as phantom_page_info:
                components.Button(
                    self.page, selector="//app-wallet-button[@label='From']//*[text()='Connect Wallet']").click()
                components.Button(
                    self.page, selector="//app-wallets-dialog//*[text()='Phantom']/parent::*").click()
            self._handle_phantom_unlock(phantom_page_info.value)
            self.page.wait_for_selector(
                selector="//app-wallet-button[@label='From']//*[contains(text(),'B4t7')]", timeout=timeout)
        except TimeoutError as e:
            if 'waiting for event "page"' not in e.message:
                raise e

    @allure.step("Connect Metamask Wallet")
    def connect_metamask(self, timeout: float = 30000) -> None:
        """Connect Metamask Wallet"""
        # Wait page loaded
        if self._is_target_tab_loaded:
            pass
        try:
            with self.page.context.expect_page(timeout=timeout) as mm_page_connect:
                components.Button(
                    self.page, selector="//app-wallet-button[@label='To']//*[text()='Connect Wallet']").click()
                components.Button(self.page, selector="w3m-wallet-button[name='MetaMask']").click()
            self._handle_metamask_connect(mm_page_connect.value)
            self.page.wait_for_selector(
                selector="//app-wallet-button[@label='To']//*[contains(text(),'0x4701')]", timeout=timeout)
        except TimeoutError as e:
            if 'waiting for event "page"' not in e.message:
                raise e

    @allure.step("Set source token to {token} and amount to {amount}")
    def set_source_token(self, token: str, amount: float) -> None:
        """Set source token and amount ti transfer"""
        components.Button(self.page, text="Select token").click()
        self.page.wait_for_selector(selector="//div[contains(@class, 'tokens-options')]")
        components.Button(self.page, selector=f"//button//*[text()='{token}']").click()
        self.page.wait_for_selector(selector="//label[contains(text(), 'balance')]")
        components.Input(self.page, selector="//input[contains(@class, 'token-amount-input')]").fill(str(amount))

    @allure.step("Set transaction fee for platform {platform}, token {token_name} and fee type {fee_type}")
    def set_transaction_fee(self, platform: str, token_name: str, fee_type: str) -> None:
        """Set Neon transaction fee type"""
        if platform != Platform.solana or token_name != Tokens.neon.name:
            return
        selector = f"//app-neon-transaction-fee//*[contains(text(),'{fee_type}')]/parent::*"
        components.Button(self.page, selector=selector).click()
        expect(self.page.locator(selector + "[contains(@class, 'selected')]")).to_be_visible()

    def next_tab(self) -> None:
        """Got to next tab"""
        button = self.page.wait_for_selector(selector="//div[contains(@class, 'button') and text()='Next']")
        button.click()

    @allure.step("Confirm tokens transfer for platform {platform} and {token}")
    def confirm_tokens_transfer(self, platform: str, token: Token, timeout: float = 60000) -> None:
        """Confirm tokens withdraw"""
        try:
            with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
                self.page.wait_for_selector(selector="//button[contains(@class, 'transfer-button')]").click()
        except TimeoutError as e:
            raise AssertionError("expected new window with wallet confirmation page") from e

        confirm_page = confirm_page_info.value

        if platform == Platform.solana:
            if token in [libs.Tokens.sol]:
                try:
                    with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
                        self._handle_pt_withdraw_confirm(confirm_page)
                except TimeoutError as e:
                    raise AssertionError("expected new window with Phantom confirmation page") from e
                confirm_page = confirm_page_info.value
            self._handle_pt_withdraw_confirm(confirm_page)

        if platform == Platform.neon:
            if token in [libs.Tokens.wsol, libs.Tokens.usdt, libs.Tokens.usdc]:
                try:
                    with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
                        self._handle_pt_withdraw_confirm(confirm_page)
                except TimeoutError as e:
                    raise AssertionError("expected new window with MetaMask confirmation page") from e
                confirm_page = confirm_page_info.value
            self._handle_mm_withdraw_confirm(confirm_page)

        # Close overlay message 'Transfer complete'
        expect(self.page.get_by_role("heading", name="Transfer complete")).to_be_visible(timeout=timeout)
        components.Button(self.page, selector="//*[text()='Close']").click()
        self.page_loaded()
