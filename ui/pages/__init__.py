import time

from playwright.sync_api import Page


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.page_loaded()
        self._menu = None

    def page_loaded(self):
        raise NotImplementedError("Override this method in your page")

    @property
    def menu(self):
        if self._menu is None:
            self._menu = Menu(page=self.page)
        return self._menu

    @property
    def url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    def reload(self, timeout=0):
        return self.page.reload(timeout=timeout)

    @property
    def text_from_tooltip(self) -> str:
        return self.page.wait_for_selector(
            "//div[contains(@id, 'tooltip') and @role='tooltip']", state="visible", timeout=30000
        ).inner_text()


class Menu:
    _menu_selector: str = None
    _header_selector: str = None

    def __init__(self, page: Page, header_selector: str, menu_selector: str):
        self.page = page
        self._menu_selector = menu_selector
        self._header_selector = header_selector

    def select_item(self, selector: str) -> None:
        if not self.is_open():
            self.open()
        self.page.click(selector)

    def is_open(self):
        return self.page.is_visible(self._header_selector, timeout=0)

    def open(self):
        if not self.is_open():
            self.page.click(self._menu_selector)
            self.page.wait_for_selector(self._header_selector, state="visible", timeout=50)

    def close(self):
        if self.is_open():
            self.page.click(self._menu_selector)
            self.page.wait_for_selector(self._header_selector, state="hidden", timeout=10)
