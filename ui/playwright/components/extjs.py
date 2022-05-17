import typing as tp

from playwright.sync_api import Page


class Button:
    def __init__(
        self,
        page: Page,
        text: tp.Optional[str] = None,
        icon: tp.Optional[str] = None,
        selector: tp.Optional[str] = None,
    ):
        self.page = page
        if text:
            self._selector = f'//span[text()="{text}"]/ancestor::a'
        elif icon:
            self._selector = f'//span[contains(@class, "{icon}")]/ancestor::a'
        elif selector:
            self._selector = selector
        else:
            raise AssertionError("Provide text or icon name for button")

    def click(self):
        self.page.wait_for_selector(self._selector).click()


class LoadingModal:
    def __init__(self, page: Page, text: str):
        self.page = page
        self._text = text

    def wait(
        self,
        state: tp.Union[tp.Literal["attached", "detached", "hidden", "visible"], None] = "visible",
    ):
        self.page.wait_for_selector(
            f'//div[text()="{self._text}"]/ancestor::div', state=state, timeout=10000
        )


class RefreshModal:
    def __init__(self, page: Page):
        self.page = page

    def refresh(self):
        Button(
            page=self.page, selector='//a[contains(@class, "x-btn") and @data-qtip="Refresh"]'
        ).click()
        loader = self.page.query_selector(
            '//div[@class=" x-grid-buffered-loader"]/div[text()="Loading..."]'
        )
        loader.wait_for_element_state("hidden")
