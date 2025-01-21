from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from utils.base_page import BasePage
from selenium.webdriver.support import expected_conditions as EC


class Menu(BasePage):
    developers_link = (By.XPATH, "//div[@class='dropdown__link link'][contains(.,'Developers')]")
    link_on_github_in_menu = (By.XPATH, "(//span[contains(.,'GitHub')])[2]")
    ecosystem_link = (By.XPATH, "(//div[@class='dropdown__link link'][contains(.,'Ecosystem')]")
    link_on_neonpass = (By.XPATH, "(//span[contains(.,'NeonPass')])[4]")

    def click_on_menu_developers_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.developers_link)).click()

    def check_dropdown_in_menu_developers_github_link(self):
        for_developers = self.wait.until(EC.presence_of_element_located(Menu.developers_link))
        ActionChains(self.driver).move_to_element(for_developers).perform()
        element = self.wait.until(EC.presence_of_element_located(Menu.link_on_github_in_menu))
        assert element.text == "GitHub"

    def click_on_github_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.link_on_github_in_menu)).click()

    def check_dropdown_in_menu_ecosystem_neonpass_link(self):
        ecosystem = self.wait.until(EC.presence_of_element_located(Menu.ecosystem_link))
        ActionChains(self.driver).move_to_element(ecosystem).perform()
        element = self.wait.until(EC.presence_of_element_located(Menu.link_on_neonpass))
        assert element.text == "NeonPass"

    def click_on_neonpass_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.link_on_neonpass)).click()
