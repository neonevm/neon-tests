import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_page import BasePage


class DeveloperPage(BasePage):
    _url = "https://neonevm.org/developers"

    build_on_neon_link_block = (By.XPATH, "//a[text()='Build on Neon']")

    @allure.step("Click on the 'Build on Neon' button")
    def click_on_build_on_neon_link_block(self):
        self.wait.until(EC.presence_of_element_located(DeveloperPage.build_on_neon_link_block)).click()

    @allure.step("Check 'Build on Neon' button is visible")
    def assert_text_on_build_on_neon_block_link(self):
        self.wait.until(EC.presence_of_element_located(DeveloperPage.build_on_neon_link_block))
