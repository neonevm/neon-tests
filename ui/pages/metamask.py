# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""
import typing as tp

from . import BasePage, Menu
from ui import components


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

    _networks_menu: Menu = None

    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskAccountsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector(
            "//button[@class='selected-account__clickable']/descendant::div[text()='Account 1']"
        )

    @property
    def networks_menu(self) -> Menu:
        if not self._networks_menu:
            self._networks_menu = Menu(
                self.page,
                header_selector="//div[@class='network-dropdown-title' and text()='Networks']",
                menu_selector="//div[contains(@class, 'network-display--clickable') and @role='button']",
            )
        return self._networks_menu

    @property
    def current_network(self) -> str:
        return self.page.query_selector("//div[contains(@class, 'network-display')]/span").text_content()

    def change_network(self, name) -> None:
        """Select EVM network"""
        if self.current_network != name:
            self.networks_menu.select_item(f"//li[@class='dropdown-menu-item']/span[text()='{name}']")
