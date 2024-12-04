from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from utils.base_class import BaseClass
from selenium.webdriver.support import expected_conditions as EC

class Menu(BaseClass):

    developers_link = (By.XPATH, "(//a[@href='/developers'][contains(.,'Developers')])[2]")
    link_on_github_in_menu = (By.XPATH, "(//div[contains(@class,'dropdown__list')])[1]//div[3]//span[1]")
    ecosystem_link = (By.XPATH, "(//a[@href='/ecosystem'][contains(.,'Ecosystem')])[2]")
    link_on_neonpass = (By.XPATH, "(//div[contains(@class,'dropdown__list')])[2]//div[3]//span[1]")

    def click_on_menu_developers_link(self):
        self.wait.until(EC.presence_of_element_located(Menu.developers_link)).click()

    def check_dropdown_in_menu_developers_github_link(self):
        for_developers = self.wait.until(EC.presence_of_element_located(Menu.developers_link))
        ActionChains(self.driver).move_to_element(for_developers).perform()
        assert self.wait.until(EC.presence_of_element_located(Menu.link_on_github_in_menu)).text == "GitHub"
        self.wait.until(EC.presence_of_element_located(Menu.link_on_github_in_menu)).click()

    def check_dropdown_in_menu_ecosystem_neonpass_link(self):
        ecosystem = self.wait.until(EC.presence_of_element_located(Menu.ecosystem_link))
        ActionChains(self.driver).move_to_element(ecosystem).perform()
        assert self.wait.until(EC.presence_of_element_located(Menu.link_on_neonpass)).text == "NeonPass"
        self.wait.until(EC.presence_of_element_located(Menu.link_on_neonpass)).click()