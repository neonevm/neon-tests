# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""
import pyperclip3 as clipboard

from ui import libs
from ui import components
from . import BasePage


class MetaMaskWelcomePage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskWelcomePage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//button[contains(@class, 'first-time-flow__button')]")

    def start_work(self) -> None:
        components.Button(self.page, selector="//button[contains(@class, 'first-time-flow__button')]").click()


class MetaMaskLoginPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskLoginPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//div[contains(@class, 'app-header__logo-container--clickable')]")

    def login(self, password: str) -> "MetaMaskAccountsPage":
        components.Input(self.page, element_id="password").fill(password)
        components.Button(self.page, selector="//input[@id='password']/following::button").click()
        return MetaMaskAccountsPage(self.page)


class MetaMaskAccountsPage(BasePage):

    _networks_menu: components.Menu = None
    _accounts_menu: components.Menu = None

    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskAccountsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector(
            "//button[@class='selected-account__clickable']/descendant::div[text()='Account 1']"
        )

    @property
    def networks_menu(self) -> components.Menu:
        if not self._networks_menu:
            self._networks_menu = components.Menu(
                self.page,
                header_selector="//div[@class='network-dropdown-title' and text()='Networks']",
                menu_selector="//div[contains(@class, 'network-display--clickable') and @role='button']",
            )
        return self._networks_menu

    @property
    def accounts_menu(self) -> components.Menu:
        if not self._accounts_menu:
            self._accounts_menu = components.Menu(
                self.page,
                header_selector="//div[contains(@class, 'account-menu__header') and text()='My Accounts']",
                menu_selector="//div[@class='account-menu__icon']",
            )
        return self._accounts_menu

    @property
    def current_network(self) -> str:
        return self.page.query_selector("//div[contains(@class, 'network-display')]/span").text_content()

    @property
    def active_account(self) -> str:
        return self.page.query_selector("//div[@class='selected-account__name']").text_content()

    @property
    def active_account_address(self) -> str:
        clipboard.clear()
        components.Button(self.page, selector="//button[@class='selected-account__clickable']").click()
        return clipboard.paste()

    @property
    def active_account_neon_balance(self) -> float:
        return self._get_balance(self.active_account, libs.Tokens.neon)

    @property
    def active_account_usdt_balance(self) -> float:
        return self._get_balance(self.active_account, libs.Tokens.usdt)

    def change_network(self, network: str) -> None:
        """Select EVM network"""
        if self.current_network != network:
            self.networks_menu.select_item(f"//li[@class='dropdown-menu-item']/span[text()='{network}']")

    def change_account(self, account: str) -> None:
        """Select account"""
        if self.active_account != account:
            self.accounts_menu.select_item(f"//div[@class='account-menu__name' and text()='{account}']")

    def _get_balance(self, account: str, token: str) -> float:
        """Return token balance on account"""
        if self.active_account != account:
            self.change_account(account)
        return float(
            self.page.wait_for_selector(
                f"//button[contains(@title, '{token}')]/descendant::span[@class='asset-list-item__token-value']"
            ).text_content()
        )

    def check_funds_protection(self) -> None:
        """Check MetaMask funds protection"""
        el = self.page.query_selector("//h2[text()='Protect your funds']/following::button[text()='Got it']")
        if el:
            el.click()
