import typing as tp

from playwright.sync_api import Page


class Button:
    def __init__(
        self, page: Page, text: tp.Optional[str] = None, selector: tp.Optional[str] = None, timeout: int = 300
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
        self.close()

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


class CheckBox:
    def __init__(self, page: Page, selector: str) -> None:
        self.page = page
        self._selector = selector

    def check(self) -> None:
        self.page.click(selector=self._selector)

    @property
    def is_checked(self) -> bool:
        return self.page.query_selector(selector=self._selector).is_checked()


class Combobox:
    elems_selector = '//div[contains(@class, "style__menuContainer")]'

    def __init__(
        self,
        page: Page,
        selector: tp.Optional[str] = None,
    ) -> None:
        self.page = page
        self._component = self.page.query_selector(selector)

    def open(self) -> None:
        if not self.is_open():
            self._component.wait_for_selector('//*[contains(@class, "style__loader")]', state="detached")
            self._component.click()

    def is_open(self) -> bool:
        return bool(self.page.query_selector(self.elems_selector))

    def close(self) -> None:
        if self.is_open():
            self._component.click()

    def get_items(self) -> tp.List["ElementHandle"]:
        if not self.is_open():
            self.open()
        return self.page.query_selector_all('//div[contains(@class, "style__option")]/span')

    def set_item(self, name: str) -> None:
        self.open()
        self.page.click(f'//div[contains(@class, "style__option")]/span[text()="{name}"]')
