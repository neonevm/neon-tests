import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class DeveloperPage:
    def __init__(self, driver):
        self.driver = driver

    build_on_neon_link_block = (By.XPATH, "//a[contains(.,'Build on Neon')]")
    developers_url = "https://neonevm.org/developers"

    def click_on_build_on_neon_link_block(self):
        self.driver.find_element(*DeveloperPage.build_on_neon_link_block).click()

    def assert_text_on_build_on_neon_block_link(self):
        assert "Build on Neon" == self.driver.find_element(*DeveloperPage.build_on_neon_link_block).text

    def assert_developers_page_url(self, url=developers_url):
        self.driver.switch_to.window(self.driver.window_handles[1])
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be(url))
        URL = self.driver.current_url
        assert url == URL, "URLs are different!"

    def assert_page_url(self, url=developers_url):
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be(url))
        URL = self.driver.current_url
        assert url == URL, "URLs are different!"
