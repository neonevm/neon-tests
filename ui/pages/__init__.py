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
    menu_selector = "a.x-btn-scalr"
    item_selector = ".x-box-item:not(.x-menu-item-separator)"

    def __init__(self, page: Page):
        self.page = page
        self._menu_id = None

    def _get_menu_id(self):
        return self.page.get_attribute(self.menu_selector, "aria-owns")

    @property
    def menu_id(self):
        if self._menu_id is None:
            self._menu_id = self._get_menu_id()
        return self._menu_id

    def get_items(self):
        self.open()
        menu = self.page.wait_for_selector(f'[data-componentid="{self.menu_id}"]', timeout=500)
        items = menu.query_selector_all(self.item_selector)
        self.close()
        time.sleep(0.3)
        return items

    def is_open(self):
        return self.page.is_visible(f"{self.menu_selector}.x-btn-menu-active", timeout=0)

    def open(self):
        if not self.is_open():
            self.page.wait_for_selector(
                f"{self.menu_selector}:not(.x-btn-menu-active)", timeout=1000
            )
            self.page.click(self.menu_selector)
            self.page.wait_for_selector(
                f'[data-componentid="{self.menu_id}"]', state="visible", timeout=5000
            )

    def close(self):
        if self.is_open():
            self.page.click(self.menu_selector)
            self.page.wait_for_selector(
                f'[data-componentid="{self.menu_id}"]', state="hidden", timeout=1000
            )
