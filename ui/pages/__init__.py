from playwright.sync_api import Page


class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.page_loaded()
        self._menu = None

    def page_loaded(self):
        raise NotImplementedError("Override this method in your page")

    @property
    def url(self) -> str:
        return self.page.url

    @property
    def title(self) -> str:
        return self.page.title()

    def reload(self, timeout=0):
        return self.page.reload(timeout=timeout)

