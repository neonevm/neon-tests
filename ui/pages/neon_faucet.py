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
    SELECTORS = {
        "connect_wallet_message": "//div[text()='Connect your wallet to get tokens']",
        "connect_metamask_btn": "//div[text()='Connect MetaMask']",
        "success_message": "//h1[text()='Choose the token type and the amount to be airdropped.']",
        "choose_token_btn": "//span[text()='Choose Token']",
        "token_option": "//div[@class='text-base' and text()='{}']",
        "token_search": "//input[contains(@placeholder,'Search token...')]",
        "token_amount_input": "//input[@title='Token Amount']",
        "send_button": "//div[contains(@class, 'button--light')]",
        "transfer_success": "//h2[text()='Transfer Successful']",
        "neonpass_button": "//a[text()='NeonPass']",
        "limit_exceeded": "//div[contains(text(),'Maximum limit for one airdrop is 100 tokens per minute')]",
        "install_wallet_msg": "//div[text()='Please install a wallet that supports NEON network']",
        "too_many_requests": "//p[text()='For security reasons, please wait a minute before making a new request']",
        "airdrop_enabled": "//div[not(contains(@class, 'button--disabled')) and span[text()='send test tokens']]",
        "help_button": "//a[text()='Help']",
        "neon_website_button": "//a[text()='Neon Website']",
        "token_search_results": "//div[contains(@class,'overflow-y-auto')]/div",
    }

    def __init__(self, *args, **kwargs) -> None:
        super(NeonTestAirdropsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector(self.SELECTORS["connect_wallet_message"])

    def connect_wallet(self, timeout: int = 300) -> None:
        components.Button(self.page, selector=self.SELECTORS["connect_metamask_btn"]).click()
        self.page.wait_for_selector(self.SELECTORS["success_message"], timeout=timeout)

    def _choose_token(self, token: str) -> None:
        self.page.query_selector(self.SELECTORS["choose_token_btn"]).click()
        self.page.wait_for_selector(self.SELECTORS["token_option"].format(token)).click()

    def choose_non_existing_token(self, token: str) -> None:
        self.page.query_selector(self.SELECTORS["choose_token_btn"]).click()
        self.page.wait_for_selector(self.SELECTORS["token_search"]).type(token)
        tokens = self.page.query_selector_all(self.SELECTORS["token_search_results"])
        assert len(tokens) == 0, f"Expected no tokens, but found {len(tokens)}"

    def _set_amount(self, amount: tp.Union[int, str]) -> None:
        self.page.query_selector(self.SELECTORS["token_amount_input"]).fill(str(amount))

    def send_tokens(self, token: str, amount: tp.Union[int, str]) -> None:
        self._choose_token(token)
        self._set_amount(amount)

    def click_transfer_btn(self) -> None:
        self.page.wait_for_selector(self.SELECTORS["send_button"]).click()

    def check_sucessfull_sent(self) -> None:
        self.page.wait_for_selector(self.SELECTORS["transfer_success"])

    @allure.step("Text on exceeding the limit is displayed")
    def text_too_much_tokens(self, token: str, amount: tp.Union[int, str]) -> None:
        self._choose_token(token)
        self._set_amount(amount)
        self.page.wait_for_selector(self.SELECTORS["limit_exceeded"])

    @allure.step("Click 'Help' button")
    def help_button_click(self) -> None:
        self.page.click(self.SELECTORS["help_button"])

    @allure.step("Click 'Neon Website' button")
    def neon_website_button_click(self) -> None:
        self.page.click(self.SELECTORS["neon_website_button"])

    @allure.step("Click 'NeonPass' button")
    def neonpass_button_click(self) -> None:
        self.page.click(self.SELECTORS["neonpass_button"])

    @allure.step("Check install wallet message")
    def install_wallet_message(self) -> None:
        self.page.text_content(self.SELECTORS["install_wallet_msg"])

    @property
    def is_airdrop_enabled(self) -> bool:
        return bool(self.page.query_selector(self.SELECTORS["airdrop_enabled"]))

    @allure.step("Reload page")
    def reload_page(self) -> None:
        self.page.reload()

    @allure.step("Too many request notification exists")
    def wait_for_too_many_requests_notification(self, timeout: int = 3000) -> None:
        self.page.wait_for_selector(
            self.SELECTORS["too_many_requests"],
            timeout=timeout,
            state="visible",
        )
