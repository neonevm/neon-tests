from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.base_class import BaseClass

class ExternalPages(BaseClass):

    quick_start_url = "https://neonevm.org/docs/quick_start"
    google_forms_url = "https://docs.google.com/forms/d/15iL4l-Rj3GUdtE1tlQTto2sqgMS5Gpn92u0GUveWWVg/viewform?edit_requested=true"
    github_url = "https://github.com/neonevm/neon-evm"
    check_google_forms_title = (By.XPATH, "//div[contains(text(),'Join our')]")

    def assert_text_on_googleform_title(self):
        assert "Join our Ecosystem" == self.wait.until(EC.presence_of_element_located(ExternalPages.check_google_forms_title)).text

    def assert_neon_docs_page_url(self, url=quick_start_url):
        self.driver.switch_to.window(self.driver.window_handles[1])
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be(url))
        URL = self.driver.current_url
        assert url == URL, "the url is {URL}"

    def assert_google_forms_page_url(self,url=google_forms_url):
        self.driver.switch_to.window(self.driver.window_handles[1])
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be(url))
        URL = self.driver.current_url
        assert url == URL, "the url is {URL}"

    def assert_github_page_url(self,url=github_url):
        self.driver.switch_to.window(self.driver.window_handles[1])
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be(url))
        URL = self.driver.current_url
        assert url == URL, "the url is {URL}"
