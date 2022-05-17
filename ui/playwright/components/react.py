import logging
import typing as tp

LOG = logging.getLogger(__name__)

from playwright._impl._api_types import TimeoutError
from playwright.sync_api import Page


class CheckBox:
    def __init__(self, page: Page, selector: str) -> None:
        self.page = page
        self._selector = selector

    def check(self) -> None:
        self.page.click(selector=self._selector)

    @property
    def is_checked(self) -> bool:
        return self.page.query_selector(selector=self._selector).is_checked()


class SelectorButton:
    def __init__(self, page: Page, text: str) -> None:
        self.page = page
        self._text = text

    def click(self) -> None:
        self.page.click(f"div[role='button'] >> text='{self._text}'")


class Button:
    def __init__(
        self, page: Page, text: tp.Optional[str] = None, selector: tp.Optional[str] = None
    ) -> None:
        self.page = page
        self._selector = selector or f'//span[text()="{text}"]/ancestor::button'

    def click(self) -> None:
        self.page.click(self._selector)


class Input:
    def __init__(
        self,
        page: Page,
        placeholder: tp.Optional[str] = None,
        title: tp.Optional[str] = None,
        label: tp.Optional[str] = None,
        selector: tp.Optional[str] = None,
    ) -> None:
        self.page = page
        if selector:
            self._selector = selector
        elif placeholder:
            self._selector = f'//input[@placeholder="{placeholder}"]'
        elif title:
            self._selector = f'//h2[text()="{title}:"]/following-sibling::div//input'
        elif label:
            self._selector = f'//label[text()="{label}"]/following-sibling::div//input'

    def fill(self, text: str) -> None:
        el = self.page.query_selector(self._selector)
        if el:
            el.fill(text)
            return
        raise AssertionError(f"Input element with selector: '{self._selector}' not found")


class Combobox:

    elems_selector = '//div[contains(@class, "style__menuContainer")]'

    def __init__(
        self,
        page: Page,
        placeholder: tp.Optional[str] = None,
        label: tp.Optional[str] = None,
        selector: tp.Optional[str] = None,
    ) -> None:
        self.page = page
        if placeholder:
            selector = (
                f'//div[contains(@class, "style__placeholder") and text() = "{placeholder}"]/../..'
            )
        elif label:
            selector = f'//label[text()="{label}"]/following-sibling::div/div/div/div'
        self._component = self.page.query_selector(selector)

    def open(self) -> None:
        if not self.is_open():
            self._component.wait_for_selector(
                '//*[contains(@class, "style__loader")]', state="detached"
            )
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


class Notification:
    def __init__(self, page: Page, text: str) -> None:
        self.page = page
        self._text = text

    def exist(self) -> tp.Optional["ElementHandle"]:
        return self.page.wait_for_selector(
            f'//div[text()="{self._text}"]/ancestor::div[contains(@class, "style__notification")]'
        )

    def close(self) -> None:
        self.page.click('//div[contains(@class, "style__sidebar")]')


class RefreshModal:
    """Refresh statys"""

    def __init__(self, page: Page) -> None:
        self.page = page

    def refresh(self) -> None:
        button = Button(page=self.page, selector='//span[text()="Refresh"]/ancestor::button')
        for attempt in range(5):
            button.click()
            try:
                loader = self.page.wait_for_selector(
                    selector='//div[text()="LOADING"]', state="attached"
                )
                loader.wait_for_element_state("hidden")
                return
            except TimeoutError:
                LOG.info(f"Refreshing, wait for selector, attempt {attempt}, timeout exceeded")
        else:
            raise TimeoutError("Timeout exceeded.")
