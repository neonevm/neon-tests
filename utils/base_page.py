import pytest
import abc
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select


@pytest.mark.usefixtures("setup")
class BasePage(abc.ABC):
    _url: str

    def __init__(self, driver, url=None):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 10)
        self.url = url or self._url

    def select_option_by_text(self, locator, text):
        sel = Select(locator)
        sel.select_by_visible_text(text)

    def assert_page_url(self, url=None):
        if url is None:
            url = self._url
        self.wait.until(EC.url_to_be(url))
        current_url = self.driver.current_url
        assert url == current_url, f"The url is {current_url}"

    def switch_window(self, index: int):
        WebDriverWait(self.driver, 10).until(lambda driver: len(driver.window_handles) > index)
        self.driver.switch_to.window(self.driver.window_handles[index])

    def assert_windows_count(self, expected_windows_count: int):
        assert (
            len(self.driver.window_handles) == expected_windows_count
        ), f"Expected {expected_windows_count} windows, but found {len(self.driver.window_handles)}"

    def close_current_tab(self):
        self.driver.close()

    def reload_page(self):
        self.driver.refresh()

    def clear_local_storage(self):
        self.driver.execute_script("window.localStorage.clear();")
