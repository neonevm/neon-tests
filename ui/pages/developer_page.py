import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.base_class import BaseClass

class DeveloperPage(BaseClass):
    _url = "https://neonevm.org/developers"

    build_on_neon_link_block = (By.XPATH, "//a[contains(.,'Build on Neon')]")
    text_on_block = "Build on Neon"
    #developers_url = "https://neonevm.org/developers"

    def click_on_build_on_neon_link_block(self):
        self.wait.until(EC.presence_of_element_located(DeveloperPage.build_on_neon_link_block)).click()

    def assert_text_on_build_on_neon_block_link(self):
        assert DeveloperPage.text_on_block == self.wait.until(EC.presence_of_element_located(DeveloperPage.build_on_neon_link_block)).text

    def assert_page_url(self, url=None):
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be(url))
        URL = self.driver.current_url
        assert url == URL, "the url is {URL}"
