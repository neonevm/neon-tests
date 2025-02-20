import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_page import BasePage


class FaucetPage(BasePage):

    neon_website_url = "https://neonevm.org/"
    neonpass_url = "https://neonpass.live/"
    faucet_docs_url = "https://neonevm.org/docs/developing/utilities/faucet"

    neon_website_button = (By.XPATH, "//a[contains(.,'Neon Website')]")
    neonpass_button = (By.XPATH, "//a[contains(.,'NeonPass')]")
    help_button = (By.XPATH, "//a[contains(.,'Help')]")

    @allure.step("Click 'Neon Website' button")
    def click_neon_website_button(self):
        self.wait.until(EC.visibility_of_element_located(FaucetPage.neon_website_button)).click()

    @allure.step("Click 'NeonPass' button")
    def click_neonpass_button(self):
        self.wait.until(EC.visibility_of_element_located(FaucetPage.neonpass_button)).click()

    @allure.step("Click 'Help' button")
    def click_help_button(self):
        self.wait.until(EC.visibility_of_element_located(FaucetPage.help_button)).click()
