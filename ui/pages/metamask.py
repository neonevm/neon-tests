# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""
from __future__ import annotations

import allure
import pyperclip3 as clipboard
from playwright._impl._errors import TimeoutError

from ui import components
from ui import libs
from ui.constants import PLATFORM_NETWORKS
from ui.pages import phantom
from . import BasePage
from ..libs import Token


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
        self.page.wait_for_selector("//button[contains(@class, 'app-header__logo-container')]")

    def login(self, password: str) -> MetaMaskPopoverNewsPage:
        self.page.wait_for_selector("//input[@id='password']")
        components.Input(self.page, element_id="password").fill(password)
        components.Button(self.page, selector="//input[@id='password']/following::button").click()
        return MetaMaskPopoverNewsPage(self.page)


class MetaMaskConnectPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskConnectPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//*[text()='Connect with MetaMask']")

    def next(self):
        components.Button(self.page, text="Next").click()

    def connect(self):
        components.Button(self.page, text="Connect").click()


class MetaMaskPopoverNewsPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskPopoverNewsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//section[contains(@class,'whats-new-popup__popover')]")

    def close(self) -> MetaMaskAccountsPage:
        components.Button(self.page, selector="//button[contains(@data-testid, 'popover-close')]").click()
        return MetaMaskAccountsPage(self.page)


class MetaMaskAccountsPage(BasePage):
    SELECTORS = {
        "account_icon_name": "//button[@data-testid='account-menu-icon']/descendant::span[text()='{account_name}']",
        "account_menu_button": "//button[@data-testid='account-menu-icon']",
        "account_list_item": "//button[contains(@class, 'multichain-account-list-item__account-name') and text()='{account}']",
        "asset_tab_button": "//*[@data-testid='home__asset-tab']/button",
        "activity_tab_button": "//button[text()='Activity']",
        "next_button": "//button[text()='Next']",
        "connect_button": "//button[text()='Connect']",
        "select_wallets_checkbox": "//input[contains(@class, 'choose-account-list__header-check-box')]",
        "address_copy_button": "//button[@data-testid='address-copy-button-text']",
        "funds_protection_popup": "//h2[text()='Protect your funds']/following::button[text()='Got it']",
        "accounts_menu_header": "//header[text()='Select an account']",
        "accounts_menu_items": "//div[contains(@class, 'multichain-account-list-item__account-name')]",
        "networks_menu_header": "//div[@class='network-dropdown-title' and text()='Networks']",
        "networks_menu_items": "//div[contains(@class, 'multichain-network-list-item')]",
        "current_network": "//button[contains(@data-testid, 'network-display')]/span",
        "active_account": "//button[@data-testid='account-menu-icon']/span",
        "network_option": "//li[@class='dropdown-menu-item']/span[text()='{}']",
        "account_button": "//button[@data-testid='account-menu-icon']",
        "account_option": "//button[contains(@class, 'multichain-account-list-item__account-name') and text()='{}']",
        "token_balance": (
            "//*[@data-testid='multichain-token-list-button']//*[text()='{token}']"
            "/../../../*[@data-testid='multichain-token-list-item-value']"
        ),
    }

    _networks_menu: components.Menu = None
    _accounts_menu: components.Menu = None

    def selector(self, name: str, **kwargs) -> str:
        return self.SELECTORS[name].format(**kwargs)

    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskAccountsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        account_name = self.active_account
        self.page.wait_for_selector(self.selector("account_icon_name", account_name=account_name))

    @property
    def networks_menu(self) -> components.Menu:
        if not self._networks_menu:
            self._networks_menu = components.Menu(
                self.page,
                header_selector=self.SELECTORS["networks_menu_header"],
                menu_selector=self.SELECTORS["networks_menu_items"],
            )
        return self._networks_menu

    @property
    def accounts_menu(self) -> components.Menu:
        if not self._accounts_menu:
            self._accounts_menu = components.Menu(
                self.page,
                header_selector=self.SELECTORS["accounts_menu_header"],
                menu_selector=self.SELECTORS["accounts_menu_items"],
            )
        return self._accounts_menu

    @property
    def current_network(self) -> str:
        return self.page.query_selector(self.SELECTORS["current_network"]).text_content()

    @property
    def active_account(self) -> str:
        return self.page.query_selector(self.SELECTORS["active_account"]).text_content()

    @property
    def active_account_address(self) -> str:
        clipboard.clear()
        components.Button(self.page, selector=self.SELECTORS["address_copy_button"]).click()
        return clipboard.paste()

    def switch_assets(self) -> None:
        self.page.query_selector(self.SELECTORS["asset_tab_button"]).click()

    def switch_activity(self) -> None:
        self.page.query_selector(self.SELECTORS["activity_tab_button"]).click()

    def _get_balance(self, account: str, token: str) -> float:
        if self.active_account != account:
            self.page.click(self.SELECTORS["account_button"])
            self.accounts_menu.select_item(self.SELECTORS["account_option"].format(account))
        selector = self.SELECTORS["token_balance"].format(token=token.upper())
        balance_text = self.page.wait_for_selector(selector).text_content().split(" ")[0]
        return float(balance_text)

    def select_all_accounts(self) -> None:
        self.page.click(self.SELECTORS["select_wallets_checkbox"])
        self.page.click(self.SELECTORS["next_button"])
        self.page.click(self.SELECTORS["connect_button"])

    @property
    def neon_balance(self) -> float:
        self.switch_assets()
        return self._get_balance(self.active_account, libs.Tokens.neon.name)

    @property
    def sol_balance(self) -> float:
        self.switch_assets()
        return self._get_balance(self.active_account, libs.Tokens.sol.name)

    @property
    def wsol_balance(self) -> float:
        self.switch_assets()
        return self._get_balance(self.active_account, libs.Tokens.sol.name)

    @property
    def usdt_balance(self) -> float:
        self.switch_assets()
        return self._get_balance(self.active_account, libs.Tokens.usdt.name)

    @property
    def usdc_balance(self) -> float:
        self.switch_assets()
        return self._get_balance(self.active_account, libs.Tokens.usdc.name)

    @property
    def wneon_balance(self) -> float:
        self.switch_assets()
        return self._get_balance(self.active_account, libs.Tokens.wneon.name)

    @allure.step("Get balance in the wallet")
    def get_balance(self, token: Token) -> float:
        balance = float(getattr(self, f"{token.name.lower()}_balance"))
        allure.attach(f"{token.name.lower()} balance: {balance}", "balance", allure.attachment_type.TEXT)
        return balance

    def change_network(self, network: str) -> None:
        if self.current_network != network:
            self.networks_menu.select_item(self.SELECTORS["network_option"].format(network))

    def change_account(self, account: str) -> None:
        if self.active_account == account:
            return
        components.Button(self.page, selector=self.SELECTORS["account_button"]).click()

    def check_funds_protection(self) -> None:
        el = self.page.query_selector(self.SELECTORS["funds_protection_popup"])
        if el:
            el.click()


class MetaMaskWithdrawConfirmPage(BasePage):
    def page_loaded(self):
        self.page.wait_for_selector(
            selector=f"//div[@class='confirm-page-container-header']/descendant::span[text()='{PLATFORM_NETWORKS['devnet']}']",
            timeout=30000,
        )

    def _close_withdraw_notice_box(self):
        """Close New gas experience box"""
        try:
            self.page.wait_for_selector(
                selector="//div[contains(@class, 'send__dialog') and contains(text(), 'New address detected')]"
            )
            components.Button(
                self.page,
                selector="//div[contains(@class, 'dialog--message')]/button[contains(@class, 'notice__close-button')]",
            ).click()
        except TimeoutError:
            pass

    def withdraw_confirm(self, timeout: float = 60000) -> None:
        """Confirm token transfer via neonpass"""
        self._close_withdraw_notice_box()
        try:
            with self.page.context.expect_page(timeout=timeout) as phantom_page_info:
                self.page.wait_for_selector(
                    selector="//button[contains(@class, 'button') and text()='Confirm']"
                ).click()
                phantom_page = phantom_page_info.value
                self._handle_phantom_approve(phantom_page)
        except TimeoutError as e:
            if 'waiting for event "page"' not in e.message:
                raise e

    def withdraw_reject(self) -> None:
        """Reject token transfer via neonpass"""
        self._close_withdraw_notice_box()
        self.page.wait_for_selector(selector="//button[contains(@class, 'button') and text()='Reject']").click()

    @staticmethod
    def _handle_phantom_approve(page):
        page.wait_for_load_state()
        phantom_confirm_page = phantom.PhantomWithdrawConfirmPage(page)
        phantom_confirm_page.withdraw_confirm()
