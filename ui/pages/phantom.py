# coding: utf-8
"""
Created on 2022-06-16
@author: Eugeny Kurkovich
"""

from ui import components
from . import BasePage


class PhantomUnlockPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(PhantomUnlockPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//p[text()='Enter your password']")

    def unlock(self, password: str) -> "PhantomWalletsPage":
        components.Input(self.page, placeholder="Password").fill(password)
        components.Button(self.page, selector="//button[text()='Unlock']").click()


class PhantomWalletsPage(BasePage):

    _networks_menu: components.Menu = None
    _accounts_menu: components.Menu = None

    def __init__(self, *args, **kwargs) -> None:
        super(PhantomWalletsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector(
            "//button[@class='selected-account__clickable']/descendant::div[text()='Account 1']"
        )


class PhantomWithdrawConfirmPage(BasePage):
    def page_loaded(self):
        self.page.wait_for_selector(selector="//p[text()='Approve Transaction']", timeout=10000)

    def withdraw_confirm(self) -> None:
        """Confirm tokens transfer"""
        components.Button(self.page, text="Approve").click()

    def withdraw_reject(self) -> None:
        """Reject tokens transfer"""
        components.Button(self.page, text="Cancel").click()
