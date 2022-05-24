import typing as tp

from playwright.sync_api import Page


class Button:

    def __init__(
        self,
        page: Page,
        text: tp.Optional[str] = None,
        selector: tp.Optional[str] = None,
        timeout: int = 300
    ):
        self.page = page
        self._timeout = timeout
        if text:
            self._selector = f'//button[text()="{text}"]'
        elif selector:
            self._selector = selector
        else:
            raise AssertionError("Provide text or icon name for button")

    def click(self):
        self.page.wait_for_selector(self._selector, timeout=self._timeout).click()


class Input:

    def __init__(
        self,
        page: Page,
        element_id: tp.Optional[str] = None,
        label: tp.Optional[str] = None,
        selector: tp.Optional[str] = None,
    ) -> None:
        self.page = page
        if selector:
            self._selector = selector
        elif element_id:
            self._selector = f'//input[@id="{element_id}"]'
        elif label:
            self._selector = f'//label[text()="{label}"]/following-sibling::div//input'

    def fill(self, text: str) -> None:
        el = self.page.query_selector(self._selector)
        if el:
            el.fill(text)
            return
        raise AssertionError(f"Input element with selector: '{self._selector}' not found")


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
