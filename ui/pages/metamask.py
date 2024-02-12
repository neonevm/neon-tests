# coding: utf-8
"""
Created on 2022-05-19
@author: Eugeny Kurkovich
"""
import allure
import pyperclip3 as clipboard
from playwright._impl._errors import TimeoutError

from ui import components
from ui import libs
from ui.conftest import PLATFORM_NETWORKS
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

    def login(self, password: str) -> "MetaMaskPopoverNewsPage":
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

    def close(self) -> "MetaMaskAccountsPage":
        components.Button(self.page, selector="//button[contains(@data-testid, 'popover-close')]").click()
        return MetaMaskAccountsPage(self.page)


class MetaMaskAccountsPage(BasePage):
    _networks_menu: components.Menu = None
    _accounts_menu: components.Menu = None

    def __init__(self, *args, **kwargs) -> None:
        super(MetaMaskAccountsPage, self).__init__(*args, **kwargs)

    def page_loaded(self) -> None:
        self.page.wait_for_selector("//button[@data-testid='account-menu-icon']/descendant::span[text()='Account 1']")

    @property
    def networks_menu(self) -> components.Menu:
        if not self._networks_menu:
            self._networks_menu = components.Menu(
                self.page,
                header_selector="//div[@class='network-dropdown-title' and text()='Networks']",
                menu_selector="//div[contains(@class, 'multichain-network-list-item')]",
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
        return self.page.query_selector("//button[contains(@data-testid, 'network-display')]/span").text_content()

    @property
    def active_account(self) -> str:
        return self.page.query_selector("//button[@data-testid='account-menu-icon']/span").text_content()

    @property
    def active_account_address(self) -> str:
        clipboard.clear()
        components.Button(self.page, selector="//button[@data-testid='address-copy-button-text']").click()
        return clipboard.paste()

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

    @allure.step("Get balance in the wallet")
    def get_balance(self, token: Token) -> float:
        balance = float(getattr(self, f"{token.name.lower()}_balance"))
        allure.attach(f"{token.name.lower()} balance: {balance}", "balance", allure.attachment_type.TEXT)
        return balance

    def change_network(self, network: str) -> None:
        """Select EVM network"""
        if self.current_network != network:
            self.networks_menu.select_item(f"//li[@class='dropdown-menu-item']/span[text()='{network}']")

    def change_account(self, account: str) -> None:
        """Select account"""
        if self.active_account != account:
            self.accounts_menu.select_item(f"//div[@class='account-menu__name' and text()='{account}']")

    def switch_assets(self) -> None:
        """Switch to assets tab"""
        self.page.query_selector("//*[@data-testid='home__asset-tab']/button").click()

    def switch_activity(self) -> None:
        """Switch to assets tab"""
        self.page.query_selector("//button[text()='Activity']").click()

    def _get_balance(self, account: str, token: str) -> float:
        """Return token balance on account"""
        if self.active_account != account:
            self.change_account(account)
        return float(
            self.page.wait_for_selector(
                f"//*[@data-testid='multichain-token-list-button']//*[text()='{token}']"
                f"/../../../*[@data-testid='multichain-token-list-item-value']"
            )
            .text_content()
            .split(" ")[0]
        )

    def check_funds_protection(self) -> None:
        """Check MetaMask funds protection"""
        el = self.page.query_selector("//h2[text()='Protect your funds']/following::button[text()='Got it']")
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
