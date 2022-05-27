# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""

import typing as tp

from ui import components
from . import BasePage


class NeonTestAirdropsPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(NeonTestAirdropsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//div[text()='Connect your wallet to get tokens']")

    def connect_wallet(self, timeout: int = 300) -> None:
        components.Button(self.page, selector="//div[@id='root']/descendant ::span[text()='Connect Wallet']").click()
        self.page.wait_for_selector("//h1[text()='Token dropper for test environment']", timeout=timeout)

    def _choose_token(self, token: str) -> None:
        self.page.query_selector("//span[text()='Choose Token']/parent::div[contains(@class, 'p-4')]").click()
        self.page.wait_for_selector(f"//div[@class='text-lg mb-2' and text()='{token}']").click()

    def _set_amount(self, amount: tp.Union[int, str]) -> None:
        self.page.query_selector("//input[@title='Token Amount']").fill(str(amount))

    def test_airdrop(self, token: str, amount: tp.Union[int, str]) -> None:
        self._choose_token(token)
        self._set_amount(amount)
        self.page.wait_for_selector("//div[contains(@class, 'button--light')]").click()
        self.page.wait_for_selector("//div[text()='Transferred successfully']")
