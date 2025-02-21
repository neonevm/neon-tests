import allure
from selenium.webdriver.common.by import By
from utils.base_page import BasePage
from selenium.webdriver.support import expected_conditions as EC


class Menu(BasePage):

    start_building_link = (
        By.XPATH,
        "//div[@class='dropdown__link link'][contains(.,'Developers')]/../div[@class='dropdown__list--left dropdown__list']//a[contains(.,'Start Building')]",
    )
    developers_link = (By.XPATH, "//div[@class='dropdown__link link'][contains(.,'Developers')]")
    link_on_github_in_menu = (By.XPATH, "(//span[contains(.,'GitHub')])[2]")
    news_link = (By.XPATH, "//div[@class='dropdown__link link'][contains(.,'News & Community')]")
    link_on_events = (By.XPATH, "//div[contains(@class,'dropdown__list')]//a[contains(.,'Events')]")
    ecosystem_link = (By.XPATH, "//div[@class='dropdown__link link'][contains(.,'Ecosystem')]")
    link_on_neonpass = (By.XPATH, "//div[contains(@class,'dropdown__list')]//a[contains(.,'NeonPass')]")
    link_on_solana_whitepaper = (
        By.XPATH,
        "//div[contains(@class,'dropdown__list')]//a[contains(.,'Solana Native Whitepaper')]",
    )

    solana_pdf = "https://neonevm.org/Solana_Native.pdf"
    neonpass = "https://neonpass.live/"
    events = "https://neonevm.org/events"

    @allure.step("Click on the menu item 'Developers/Start building'")
    def click_on_menu_developers_start_building_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.developers_link)).click()
        self.wait.until(EC.presence_of_element_located(Menu.start_building_link)).click()

    @allure.step("Click on the menu item 'Developers'")
    def click_on_menu_developers_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.developers_link)).click()

    @allure.step("Click on the menu item 'Ecosystem'")
    def click_on_menu_ecosystem_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.ecosystem_link)).click()

    @allure.step("Click on the menu item 'News & Community'")
    def click_on_menu_news_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.news_link)).click()

    @allure.step("Click on the menu item 'GitHub'")
    def click_on_github_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.link_on_github_in_menu)).click()

    @allure.step("Click on the menu item 'Neonpass'")
    def click_on_neonpass_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.link_on_neonpass)).click()

    @allure.step("Click on the menu item 'Solana Whitepaper'")
    def click_on_solana_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.link_on_solana_whitepaper)).click()

    @allure.step("Click on the menu item 'Events'")
    def click_on_events_link(self):
        self.wait.until(EC.visibility_of_element_located(Menu.link_on_events)).click()
