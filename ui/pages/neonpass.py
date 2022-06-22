# coding: utf-8
"""
Created on 2022-06-16
@author: Eugeny Kurkovich
"""

import os

from playwright._impl._api_types import TimeoutError

from ui import components
from ui.pages import phantom
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

    def change_transfer_source(self, source: str) -> None:
        """Change transfer source"""
        selector = f"//span[text()='From']/following-sibling::span[text()='{source}']"
        if not self.page.query_selector(selector):
            components.Button(
                self.page,
                selector="//div[contains(@class, 'flex justify-between')]/descendant::div[contains(@class, 'button')]",
            ).click()
            self.page.wait_for_selector(selector)

    def _connect_wallet(self, timeout: float = 5000):
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

    def connect_source_wallet(self, timeout: float = 5000) -> None:
        """Connect to source wallet to Neon"""
        self.page.wait_for_selector(selector="//h3[text()='Source']/following::span[text()='From']")
        self._connect_wallet(timeout=timeout)

    def connect_destination_wallet(self, timeout: float = 5000) -> None:
        """Connect destination wallet to Neon"""
        self.page.wait_for_selector(selector="//h3[text()='Target']/following::span[text()='To']")
        self._connect_wallet(timeout=timeout)

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
        self.page.wait_for_selector(selector="//div[contains(@class, 'button') and text()='Next']").click()
