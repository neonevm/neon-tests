from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_page import BasePage


class GithubPage(BasePage):
    _url = "https://github.com/neonevm/neon-evm"

    section_header = (By.XPATH, "//div[@xpath='1']")

    def assert_text_on_github_page_title(self):
        element = self.wait.until(EC.presence_of_element_located(GithubPage.section_header))
        assert element.text == "neonevm"
