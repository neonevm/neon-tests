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
