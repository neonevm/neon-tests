import allure
from selenium.webdriver.common.by import By
from utils.base_page import BasePage
from selenium.webdriver.support import expected_conditions as EC


class Menu(BasePage):

    start_building_link = (By.XPATH, "//div[contains(text(),'Developers')]/../div//a[contains(.,'Start Building')]")
    developers_link = (By.XPATH, "//div[contains(text(),'Developers')]")
    tools_link = (By.XPATH, "//div[contains(text(),'Tools')]")
    link_on_github_in_menu = (By.XPATH, "(//span[contains(.,'GitHub')])[2]")
    community_link = (By.XPATH, "//div[contains(text(),'Community')]")
    link_on_events = (By.XPATH, "//div[contains(text(),'Community')]/../div//a[contains(.,'Events')]")
    faq_link = (By.XPATH, "//a[contains(text(),'FAQ')]")
    ecosystem_link = (By.XPATH, "//header//a[contains(text(),'Ecosystem')]")
    link_on_neonpass = (By.XPATH, "//div[contains(text(),'Tools')]/../div//a[contains(.,'NeonPass Bridge')]")
    link_on_solana_whitepaper = (
        By.XPATH,
        "//div[contains(@class,'dropdown__list')]//a[contains(.,'Solana Native Whitepaper')]",
    )

    solana_pdf = "https://neonevm.org/Solana_Native.pdf"
    neonpass = "https://neonpass.live/"
    events = "https://neonevm.org/events"

    @allure.step("Click on the menu item 'Developers/Start building'")
    def click_on_menu_developers_start_building_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.developers_link)).click()
        self.wait.until(EC.visibility_of_element_located(Menu.start_building_link)).click()

    @allure.step("Click on the menu item 'Developers'")
    def click_on_menu_developers_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.developers_link)).click()

    @allure.step("Click on the menu item 'Ecosystem'")
    def click_on_menu_ecosystem_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.ecosystem_link)).click()

    @allure.step("Click on the menu item 'Community'")
    def click_on_menu_news_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.community_link)).click()

    @allure.step("Click on the menu item 'GitHub'")
    def click_on_github_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.link_on_github_in_menu)).click()

    @allure.step("Click on the menu item 'Tools/Neonpass'")
    def click_on_menu_tools_neonpass_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.tools_link)).click()
        self.wait.until(EC.visibility_of_element_located(Menu.link_on_neonpass)).click()

    @allure.step("Click on the menu item 'Solana Whitepaper'")
    def click_on_solana_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.link_on_solana_whitepaper)).click()

    @allure.step("Click on the menu item 'Events'")
    def click_on_events_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.link_on_events)).click()

    @allure.step("Click on the footer menu item 'FAQ'")
    def click_on_faq_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.faq_link)).click()
