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
        "limit_exceeded": "//div[contains(text(),'Maximum limit for one airdrop is 100 tokens per minute')]",
        "install_wallet_msg": "//div[text()='Please install a wallet that supports NEON network']",
        "too_many_requests": "//p[text()='For security reasons, please wait a minute before making a new request']",
        "airdrop_enabled": "//div[not(contains(@class, 'button--disabled')) and span[text()='send test tokens']]",
        "token_search_results": "//div[contains(@class,'overflow-y-auto')]/div",
        "menu_button": "//div[@class='py-4']//*[name()='svg']",
        "faq_link": "//a[text()=' FAQ']",
        "docs_link": "//a[text()=' Docs']",
        "twitter_link": "//a[text()=' Twitter']",
        "discord_link": "//a[text()=' Discord Community']",
        "about_neon_link": "//a[text()=' About Neon']",
        "neonpass_link": "//a[text()=' NeonPass']",
        "support_button": "//a[text()=' Support ']",
        "cookies_policy_link": "//a[text()='cookies policy']",
    }

    def __init__(self, *args, **kwargs) -> None:
        super(NeonTestAirdropsPage, self).__init__(*args, **kwargs)

    @allure.step("Wait until message 'Connect your wallet' is visible")
    def page_loaded(self) -> None:
        self.page.wait_for_selector(self.SELECTORS["connect_wallet_message"])

    @allure.step("Click 'Connect MetaMask' button'")
    def connect_wallet(self, timeout: int = 300) -> None:
        components.Button(self.page, selector=self.SELECTORS["connect_metamask_btn"]).click()
        self.page.wait_for_selector(self.SELECTORS["success_message"], timeout=timeout)

    @allure.step("Select from token {token}")
    def _choose_token(self, token: str) -> None:
        self.page.query_selector(self.SELECTORS["choose_token_btn"]).click()
        self.page.wait_for_selector(self.SELECTORS["token_option"].format(token)).click()

    @allure.step("Input into search field non-existing token")
    def choose_non_existing_token(self, token: str) -> None:
        self.page.query_selector(self.SELECTORS["choose_token_btn"]).click()
        self.page.wait_for_selector(self.SELECTORS["token_search"]).type(token)
        tokens = self.page.query_selector_all(self.SELECTORS["token_search_results"])
        assert len(tokens) == 0, f"Expected no tokens, but found {len(tokens)}"

    @allure.step("Input token amount {amount}")
    def _set_amount(self, amount: tp.Union[int, str]) -> None:
        self.page.query_selector(self.SELECTORS["token_amount_input"]).fill(str(amount))

    @allure.step("Select token and input amount")
    def send_tokens(self, token: str, amount: tp.Union[int, str]) -> None:
        self._choose_token(token)
        self._set_amount(amount)

    @allure.step("Click 'Send token' button")
    def click_transfer_btn(self) -> None:
        self.page.wait_for_selector(self.SELECTORS["send_button"]).click()

    @allure.step("Wait message 'Transfer successful' is visible")
    def check_sucessfull_sent(self) -> None:
        self.page.wait_for_selector(self.SELECTORS["transfer_success"])

    @allure.step("Text on exceeding the limit is displayed")
    def text_too_much_tokens(self, token: str, amount: tp.Union[int, str]) -> None:
        self._choose_token(token)
        self._set_amount(amount)
        self.page.wait_for_selector(self.SELECTORS["limit_exceeded"])

    @allure.step("Click 'Menu' dropdown")
    def menu_dropdown_click(self) -> None:
        self.page.click(self.SELECTORS["menu_button"])

    @allure.step("Click 'FAQ' button")
    def faq_button_click(self) -> None:
        self.page.click(self.SELECTORS["faq_link"])

    @allure.step("Click 'Docs' button")
    def docs_button_click(self) -> None:
        self.page.click(self.SELECTORS["docs_link"])

    @allure.step("Click 'About Neon' button")
    def about_neon_link_button_click(self) -> None:
        self.page.click(self.SELECTORS["about_neon_link"])

    @allure.step("Click 'Twitter' button")
    def twitter_button_click(self) -> None:
        self.page.click(self.SELECTORS["twitter_link"])

    @allure.step("Click 'Discord' button")
    def discord_button_click(self) -> None:
        self.page.click(self.SELECTORS["discord_link"])

    @allure.step("Click 'Support' button")
    def support_button_click(self) -> None:
        self.page.click(self.SELECTORS["support_button"])

    @allure.step("Click 'NeonPass' button")
    def neonpass_button_click(self) -> None:
        self.page.click(self.SELECTORS["neonpass_link"])

    @allure.step("Click 'cookies policy' link")
    def cookies_policy_link_click(self) -> None:
        self.page.click(self.SELECTORS["cookies_policy_link"])

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
