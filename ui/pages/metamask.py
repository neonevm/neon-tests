# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""
import typing as tp

from . import BasePage
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

    def login(self, password: str) -> None:
        components.Input(self.page, element_id="password").fill(password)
        components.Button(self.page, selector="//input[@id='password']/following::button").click()


class MetaMaskAccountsPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskAccountsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("")
