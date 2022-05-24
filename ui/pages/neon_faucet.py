# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""

from ui import components
from . import BasePage


class NeonTestAirdropsPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(NeonTestAirdropsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//div[text()='Connect your wallet to get tokens']")

    def connect_wallet(self) -> None:
        components.Button(self.page, selector="//div[@id='root']/descendant ::span[text()='Connect Wallet']").click()
