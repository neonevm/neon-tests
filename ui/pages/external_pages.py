from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ExternalPages:
    def __init__(self, driver):
        self.driver = driver

    check_google_forms_title = (By.XPATH, "//div[contains(text(),'Join our')]")

    def assert_text_on_googleform_title(self):
        assert "Join our Ecosystem" == self.driver.find_element(*ExternalPages.check_google_forms_title).text

    def assert_neon_docs_page_url(self):
        self.driver.switch_to.window(self.driver.window_handles[1])
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be("https://neonevm.org/docs/quick_start"))
        URL = self.driver.current_url
        assert 'https://neonevm.org/docs/quick_start' == URL, "URLs are different!"

    def assert_google_forms_page_url(self):
        self.driver.switch_to.window(self.driver.window_handles[1])
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be("https://docs.google.com/forms/d/15iL4l-Rj3GUdtE1tlQTto2sqgMS5Gpn92u0GUveWWVg/viewform?edit_requested=true"))
        URL = self.driver.current_url
        assert 'https://docs.google.com/forms/d/15iL4l-Rj3GUdtE1tlQTto2sqgMS5Gpn92u0GUveWWVg/viewform?edit_requested=true' == URL, "URLs are different!"

    def assert_github_page_url(self):
        self.driver.switch_to.window(self.driver.window_handles[1])
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be('https://github.com/neonevm/neon-evm'))
        URL = self.driver.current_url
        assert 'https://github.com/neonevm/neon-evm' == URL, "URLs are different!"
