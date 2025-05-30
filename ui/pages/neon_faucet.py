# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""

import typing as tp
import allure

from ui import components
from . import BasePage


class NeonTestAirdropsPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(NeonTestAirdropsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//div[text()='Connect your wallet to get tokens']")

    def connect_wallet(self, timeout: int = 300) -> None:
        components.Button(self.page, selector="//div[text()='Connect MetaMask']").click()
        self.page.wait_for_selector(
            "//h1[text()='Choose the token type and the amount to be airdropped.']", timeout=timeout
        )

    def _choose_token(self, token: str) -> None:
        self.page.query_selector("//span[text()='Choose Token']").click()
        self.page.wait_for_selector(f"//div[@class='text-base' and text()='{token}']").click()

    def choose_non_existing_token(self, token: str) -> None:
        list_of_tokens = "//div[contains(@class,'overflow-y-auto')]/div"
        self.page.query_selector("//span[text()='Choose Token']").click()
        self.page.wait_for_selector("//input[contains(@placeholder,'Search token...')]").type(token)
        tokens = self.page.query_selector_all(list_of_tokens)
        assert len(tokens) == 0, f"Expected no tokens, but found {len(tokens)}"

    def _set_amount(self, amount: tp.Union[int, str]) -> None:
        self.page.query_selector("//input[@title='Token Amount']").fill(str(amount))

    def send_tokens(self, token: str, amount: tp.Union[int, str]) -> None:
        self._choose_token(token)
        self._set_amount(amount)

    def click_transfer_btn(self) -> None:
        self.page.wait_for_selector("//div[contains(@class, 'button--light')]").click()

    def check_sucessfull_sent(self) -> None:
        self.page.wait_for_selector("//h2[text()='Transfer Successful']")

    @allure.step("Text on exceeding the limit is displayed")
    def text_too_much_tokens(self, token: str, amount: tp.Union[int, str]) -> None:
        self._choose_token(token)
        self._set_amount(amount)
        self.page.wait_for_selector("//div[contains(text(),'Maximum limit for one airdrop is 100 tokens per minute')]")

    @allure.step("Click 'Help' button")
    def help_button_click(self) -> None:
        self.page.click("//a[text()='Help']")

    @allure.step("Click 'Neon Website' button")
    def neon_website_button_click(self) -> None:
        self.page.click("//a[text()='Neon Website']")

    @allure.step("Click 'NeonPass' button")
    def neonpass_button_click(self) -> None:
        self.page.click("//a[text()='NeonPass']")

    @allure.step("Check install wallet message")
    def install_wallet_message(self) -> None:
        self.page.text_content("//div[text()='Please install a wallet that supports NEON network']")

    @property
    def is_airdrop_enabled(self) -> bool:
        return bool(
            self.page.query_selector(
                "//div[not(contains(@class, 'button--disabled')) and span[text()='send test tokens']]"
            )
        )

    @allure.step("Reload page")
    def reload_page(self) -> None:
        self.page.reload()

    @allure.step("Too many request notification exists")
    def wait_for_too_many_requests_notification(self, timeout: int = 3000) -> None:
        self.page.wait_for_selector(
            "//p[text()='For security reasons, please wait a minute before making a new request']",
            timeout=timeout,
            state="visible",
        )
