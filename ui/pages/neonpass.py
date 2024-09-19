# coding: utf-8
"""
Created on 2022-06-16
@author: Eugeny Kurkovich
"""

import os
from typing import Optional

import allure
from playwright._impl._errors import TimeoutError
from playwright.sync_api import expect

from ui import components
from ui.pages import phantom, metamask
from utils.consts import Time
from . import BasePage
from ..libs import Platform, Token, PriorityFee, TransactionFee


class NeonPassPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(NeonPassPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//h1[text()='NEONPASS']")

    @staticmethod
    def _handle_phantom_unlock(page) -> None:
        phantom_page = phantom.PhantomUnlockPage(page)
        phantom_page.unlock(os.environ.get("CHROME_EXT_PASSWORD"))

    @staticmethod
    def _handle_metamask_connect(page) -> None:
        mm_page = metamask.MetaMaskConnectPage(page)
        mm_page.next()
        mm_page.connect()

    @staticmethod
    def _handle_mm_withdraw_confirm(page) -> None:
        """MetaMask withdraw confirm"""
        with allure.step("MetaMask withdraw confirm"):
            page.wait_for_load_state()
            mm_confirm_page = metamask.MetaMaskWithdrawConfirmPage(page)
            mm_confirm_page.withdraw_confirm()

    @staticmethod
    def _handle_pt_withdraw_confirm(page) -> None:
        """Phantom withdraw confirm"""
        with allure.step("Phantom withdraw confirm"):
            page.wait_for_load_state()
            phantom_confirm_page = phantom.PhantomWithdrawConfirmPage(page)
            phantom_confirm_page.withdraw_confirm()

    @property
    def _is_source_tab_loaded(self) -> bool:
        """Waiting for source tab"""
        try:
            self.page.wait_for_selector(
                selector="//app-wallet-button[@label='From']//*[text()='Connect Wallet']", timeout=30000
            )
            return True
        except TimeoutError:
            return False

    @property
    def _is_target_tab_loaded(self) -> bool:
        """Waiting for target tab"""
        try:
            self.page.wait_for_selector(
                selector="//app-wallet-button[@label='To']//*[text()='Connect Wallet']", timeout=30000
            )
            return True
        except TimeoutError:
            return False

    @allure.step("Switch platform source to {platform}")
    def switch_platform_source(self, platform: str) -> None:
        """Change transfer source platform (Neon/Solana)"""
        selector = f"//app-wallet-button[@label='From']//*[text()='{platform}']"  # desired platform

        if not self.page.query_selector(selector):  # if it's not already set -> switch
            components.Button(
                self.page,
                selector="//button[@class='switch-button']",
            ).click()
            self.page.wait_for_selector(selector)

    @allure.step("Connect Phantom Wallet")
    def connect_phantom(self, timeout: float = 30000) -> None:
        """Connect Phantom Wallet"""
        # Wait page loaded
        if self._is_source_tab_loaded:
            pass
        try:
            with self.page.context.expect_page(timeout=timeout) as phantom_page_info:
                components.Button(
                    self.page, selector="//app-wallet-button[@label='From']//*[text()='Connect Wallet']"
                ).click()
                app_wallets_dialog = "//app-wallets-dialog"
                self.page.wait_for_selector(
                    selector=app_wallets_dialog + "//*[text()='Select Wallet']", timeout=timeout
                )
                components.Button(self.page, selector=app_wallets_dialog + "//*[text()='Phantom']/parent::*").click()
        except TimeoutError as e:
            if 'waiting for event "page"' not in e.message:
                raise e

        self._handle_phantom_unlock(phantom_page_info.value)
        self.page.wait_for_selector(
            selector="//app-wallet-button[@label='From']//*[contains(text(),'B4t7')]", timeout=30000
        )

    @allure.step("Connect Metamask Wallet")
    def connect_metamask(self, timeout: float = 30000) -> None:
        """Connect Metamask Wallet"""
        # Wait page loaded
        if self._is_target_tab_loaded:
            pass
        try:
            with self.page.context.expect_page(timeout=timeout) as mm_page_connect:
                components.Button(
                    self.page, selector="//app-wallet-button[@label='To']//*[text()='Connect Wallet']"
                ).click()
                self.page.locator("w3m-modal").locator("button", has_text="MetaMask").click()
                # components.Button(self.page, selector="w3m-wallet-button[name='MetaMask']").click()
            self._handle_metamask_connect(mm_page_connect.value)
        except TimeoutError as e:
            if 'waiting for event "page"' not in e.message:
                raise e

        self.page.wait_for_selector(
            selector="//app-wallet-button[@label='To']//*[contains(text(),'0x4701')]", timeout=timeout
        )

    @allure.step("Set source token to {token} and amount to {amount}")
    def set_source_token(self, token: str, amount: float) -> None:
        """Set source token and amount ti transfer"""
        components.Button(self.page, text="Select token").click()
        self.page.wait_for_selector(selector="//div[contains(@class, 'tokens-options')]")
        components.Button(
            self.page, selector=f"//div[@class='cdk-overlay-container']//button//*[text()='{token}']"
        ).click()
        self.page.wait_for_selector(selector="//label[contains(text(), 'balance')]")
        components.Input(self.page, selector="//input[contains(@class, 'token-amount-input')]").fill(str(amount))

    @allure.step("Set transaction fee {transaction_fee}")
    def set_transaction_fee(self, transaction_fee: Optional[TransactionFee]) -> None:
        """Set transaction fee type"""
        if transaction_fee is None:
            return

        fee_parent = "//app-neon-transaction-fee"
        fee_header = fee_parent + "//*[@class='header']"

        if transaction_fee.token_name in self.page.query_selector(fee_header).text_content():
            return

        components.Button(self.page, selector=fee_parent).click()
        components.Button(
            self.page, selector=fee_parent + f"//button/*[text()='{transaction_fee.network_name}']"
        ).click()

        assert transaction_fee.token_name in self.page.query_selector(fee_header).text_content()

    @allure.step("Set priority fee to {priority_fee}")
    def set_priority_fee(self, priority_fee: Optional[str]) -> None:
        """Set priority fee"""
        if priority_fee is None:
            return
        priority_fee_parent = "//app-solana-priority-fee"
        priority_fee_header = priority_fee_parent + "//*[@class='header']"

        if priority_fee in self.page.query_selector(priority_fee_header).text_content():
            return

        components.Button(self.page, selector=priority_fee_parent).click()
        components.Button(self.page, selector=priority_fee_parent + f"//button/*[text()='{priority_fee}']").click()

        if priority_fee == PriorityFee.custom:
            priority_fee_popup = "//app-priority-fee-dialog"
            # Set custom fee
            components.Input(self.page, selector=priority_fee_popup + "//input").fill("0.001")
            components.Button(self.page, selector=priority_fee_popup + "//button[@class='save']").click()

        assert priority_fee in self.page.wait_for_selector(priority_fee_header).text_content()

    def next_tab(self) -> None:
        """Got to next tab"""
        button = self.page.wait_for_selector(selector="//div[contains(@class, 'button') and text()='Next']")
        button.click()

    @allure.step("Confirm tokens transfer for platform {platform} and {token}")
    def confirm_tokens_transfer(self, platform: str, token: Token, timeout: float = 60000) -> None:
        """Confirm tokens withdraw"""
        try:
            with self.page.context.expect_page(timeout=timeout) as confirm_page_info:
                components.Button(self.page, selector="//button[contains(@class, 'transfer-button')]").click()
        except TimeoutError as e:
            raise AssertionError("expected new window with wallet confirmation page") from e

        confirm_page = confirm_page_info.value

        if platform == Platform.solana:
            self._handle_pt_withdraw_confirm(confirm_page)

        if platform == Platform.neon:
            self._handle_mm_withdraw_confirm(confirm_page)

        # Close overlay message 'Transfer complete'
        expect(self.page.get_by_role("heading", name="Transfer complete")).to_be_visible(timeout=timeout)
        components.Button(self.page, selector="//*[text()='Close']").click()
        self.page_loaded()
