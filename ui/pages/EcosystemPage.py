import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class EcosystemPage:
    def __init__(self, driver):
        self.driver = driver

    joinOurEcosystemButton = (By.XPATH, "//span[@class='button__content'][contains(.,'Join Neon EVM Ecosystem')]")

    def assert_text_on_build_on_neon_block_link(self):
        EC.visibility_of_element_located(self.driver.find_element(*EcosystemPage.joinOurEcosystemButton))

    def assert_ecosystem_page_url(self):
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be("https://neonevm.org/ecosystem"))
        URL = self.driver.current_url
        print(URL)
        assert 'https://neonevm.org/ecosystem' == URL, "URLs are different!"

