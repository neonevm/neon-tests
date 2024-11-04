from selenium.webdriver.common.by import By

class Menu:
    def __init__(self, driver):
        self.driver = driver

    developersLink = (By.XPATH, "(//a[@href='/developers'][contains(.,'Developers')])[2]")

    def click_on_menu_developers_link(self):
        self.driver.find_element(*Menu.developersLink).click()