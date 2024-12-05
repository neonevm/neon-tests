import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

@pytest.mark.usefixtures("setup")
class BaseClass:
    _url:str

    def __init__(self, driver,url=None):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 10)
        if url is None:
            url = self._url
        self.url = url

    def verify_link_presence(self, text):
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, text)))

    def no_errors_on_page(self):
        response = requests.get(self.driver.current_url)
        assert response.status_code == 200, print("Not Found.")

    def select_option_by_text(self, locator, text):
        sel = Select(locator)
        sel.select_by_visible_text(text)

    def assert_page_url(self,url=None):
        self.wait.until(EC.url_to_be(url))
        if url is None:
            url = self._url
        current_url = self.driver.current_url
        assert url == current_url, f"The url is {current_url}"

    def switch_window(self,url=None):
        self.driver.switch_to.window(self.driver.window_handles[1])
        self.wait.until(EC.url_to_be(url))
        if url is None:
            url = self._url
        current_url = self.driver.current_url
        assert url == current_url, f"the url is {current_url}"