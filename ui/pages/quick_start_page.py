import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_page import BasePage


class QuickStartPage(BasePage):
    _url = "https://neonevm.org/docs/quick_start"

    section_header = (By.XPATH, "//h1")
    quick_start_header = "Quick Start"

    @allure.step("Check text 'Quick Start' on the page header is visible")
    def assert_text_on_quick_start_page_title(self):
        element = self.wait.until(EC.presence_of_element_located(QuickStartPage.section_header))
        assert element.text == QuickStartPage.quick_start_header
