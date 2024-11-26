from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class MainPage:
    def __init__(self, driver):
        self.driver = driver

    website_url = "https://neonevm.org/"
    logo_on_header = (By.XPATH, "//*[@id='header']/div[2]/div[1]")
    logo_on_footer = (By.XPATH, "(//a[@aria-label='Go to home'])[3]")
    build_on_neon_button = (By.XPATH, "//span[contains(text(),'build on neon')]")
    start_building_button = (By.XPATH, "//a[@href='https://neonevm.org/docs/'][contains(.,'Start Building')]")
    explore_ecosystem_button = (By.XPATH, "//span[@class='button__content'][contains(.,'Explore ecosystem')]")
    explore_developer_hub_button = (By.XPATH, "//span[@class='button__content'][contains(.,'Explore developer hub')]")
    add_your_dapp_button = (By.XPATH, "//span[@class='button__content'][contains(.,'add your dapp')]")
    transaction_cost_arrow = (By.XPATH, "(//div[contains(@class,'arrow-down-icon-container')])[2]")

    def click_on_logo_on_header(self):
        self.driver.find_element(*MainPage.logo_on_header).click()

    def click_on_logo_on_footer(self):
        self.driver.find_element(*MainPage.logo_on_footer).click()

    def click_on_build_on_neon_button(self):
        self.driver.find_element(*MainPage.build_on_neon_button).click()

    def click_start_building_button(self):
        self.driver.find_element(*MainPage.start_building_button).click()

    def click_explore_ecosystem_button(self):
        self.driver.find_element(*MainPage.explore_ecosystem_button).click()

    def click_explore_developer_hub_button(self):
        self.driver.find_element(*MainPage.explore_developer_hub_button).click()

    def click_add_your_dapp_button(self):
        self.driver.find_element(*MainPage.add_your_dapp_button).click()

    def assert_main_page_url(self, website_url=website_url):
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be(website_url))
        URL = self.driver.current_url
        print(URL)
        assert website_url == URL, "URLs are different!"