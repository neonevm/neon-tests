import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_page import BasePage


class EcosystemPage(BasePage):
    _url = "https://neonevm.org/ecosystem"

    join_our_ecosystem_button = (By.XPATH, "//span[contains(.,'Join Neon EVM Ecosystem')]")

    @allure.step("Check 'Join Neon EVM Ecosystem' button is visible")
    def assert_text_on_build_on_neon_block_link(self):
        self.wait.until(EC.presence_of_element_located(EcosystemPage.join_our_ecosystem_button))
