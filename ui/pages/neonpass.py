# coding: utf-8
"""
Created on 2022-06-16
@author: Eugeny Kurkovich
"""

import os

from playwright._impl._api_types import TimeoutError

from ui import components
from ui.pages import phantom, metamask
from . import BasePage


class NeonPassPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(NeonPassPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//h3[text()='Source']")

    @staticmethod
    def _handle_phantom_unlock(page) -> None:
        page.wait_for_load_state()
        phantom_page = phantom.PhantomUnlockPage(page)
        phantom_page.page_loaded()
        phantom_page.unlock(os.environ.get("CHROME_EXT_PASSWORD"))

    @staticmethod
    def _handle_withdraw_confirm(page) -> None:
        """MetaMask withdraw confirm"""
        page.wait_for_load_state()
        try:
            mm_confirm_page = metamask.MetaMaskWithdrawConfirmPage(page)
            mm_confirm_page.withdraw_confirm()
        except TimeoutError:
            phantom_confirm_page = phantom.PhantomWithdrawConfirmPage(page)
            phantom_confirm_page.withdraw_confirm()

    @property
    def _is_source_tab_loaded(self) -> bool:
        """Waiting for source tab"""
        try:
            return self.page.wait_for_selector(
                selector="//h3[text()='Source']/following::span[text()='From']", timeout=5000
            )
        except TimeoutError:
            return False

    @property
    def _is_target_tab_loaded(self) -> bool:
        """Waiting for target tab"""
        try:
            return self.page.wait_for_selector(
                selector="//h3[text()='Target']/following::span[text()='To']", timeout=5000
            )
        except TimeoutError:
            return False

    def change_transfer_source(self, source: str) -> None:
        """Change transfer source"""
        selector = f"//span[text()='From']/following-sibling::span[text()='{source}']"
        if not self.page.query_selector(selector):
            components.Button(
                self.page,
                selector="//div[contains(@class, 'flex justify-between')]/descendant::div[contains(@class, 'button')]",
            ).click()
            self.page.wait_for_selector(selector)

    def connect_wallet(self, timeout: float = 5000) -> None:
        # Wait page laded
        if self._is_source_tab_loaded or self._is_target_tab_loaded:
            pass
        # Connect to Wallet
        try:
            with self.page.context.expect_page(timeout=timeout) as phantom_page_info:
                components.Button(
                    self.page, selector="//div[@class='flex flex-col']/descendant::*[text()='Connect Wallet']"
                ).click()
            phantom_page = phantom_page_info.value
            self._handle_phantom_unlock(phantom_page)
            self.page.wait_for_selector(
                "//div[@class='dropdown']/descendant::button[contains(text(), 'B4t7')]", timeout=timeout
            )
        except TimeoutError as e:
            if 'waiting for event "page"' not in e.message:
                raise e
            self.page.wait_for_selector(
                "//div[@class='dropdown']/descendant::div[contains(text(), '0x4701')]", timeout=timeout
            )

    def set_source_token(self, token: str, amount: float) -> None:
        """Set source token and amount ti transfer"""
        components.Button(
            self.page, selector="//div[contains(@class, 'flex-grow') and text()='Select a token']"
        ).click()
        self.page.wait_for_selector(selector="//div[contains(@class, 'ReactModal__Content--after-open')]")
        components.Input(self.page, placeholder="Choose or paste token").fill(token)
        self.page.wait_for_selector(selector=f"//div[contains(@class, 'text-lg') and text()='{token}']").click()
        self.page.wait_for_selector(selector="//span[contains(text(), 'Balance:')]")
        components.Input(self.page, selector="//input[@value='0.0']").fill(str(amount))

    def next_tab(self) -> None:
        """Got to next tab"""
        button = self.page.wait_for_selector(selector="//div[contains(@class, 'button') and text()='Next']")
        button.click()

    def confirm_tokens_transfer(self, timeout: float = 5000) -> None:
        """Confirm tokens withdraw"""
        # Confirm withdraw
        with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
            self.page.wait_for_selector(selector="//div[contains(@class, 'button') and text()='Confirm']").click()
        confirm_page = confirm_page_info.value
        self._handle_withdraw_confirm(confirm_page)
        self.page.wait_for_selector(selector="//div[text()='Transfer complete']")
        components.Button(self.page, selector="//div/*[contains(@class, 'self-end')]").click()
        self._is_source_tab_loaded
