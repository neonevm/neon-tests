from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class MainPage:
    def __init__(self, driver):
        self.driver = driver

    logoOnHeader = (By.XPATH, "//*[@id='header']/div[2]/div[1]")
    logoOnFooter = (By.XPATH, "(//a[@aria-label='Go to home'])[3]")
    buildOnNeonButton = (By.XPATH, "//span[contains(text(),'build on neon')]")
    startBuildingButton = (By.XPATH, "//a[@href='https://neonevm.org/docs/'][contains(.,'Start Building')]")
    exploreEcosystemButton = (By.XPATH, "//span[@class='button__content'][contains(.,'Explore ecosystem')]")
    exploreDeveloperHubButton = (By.XPATH, "//span[@class='button__content'][contains(.,'Explore developer hub')]")
    addYourDappButton = (By.XPATH, "//span[@class='button__content'][contains(.,'add your dapp')]")

    def click_on_logo_on_header(self):
        self.driver.find_element(*MainPage.logoOnHeader).click()

    def click_on_logo_on_footer(self):
        self.driver.find_element(*MainPage.logoOnFooter).click()

    def click_on_build_on_neon_button(self):
        self.driver.find_element(*MainPage.buildOnNeonButton).click()

    def click_start_building_button(self):
        self.driver.find_element(*MainPage.startBuildingButton).click()

    def click_explore_ecosystem_button(self):
        self.driver.find_element(*MainPage.exploreEcosystemButton).click()

    def click_explore_developer_hub_button(self):
        self.driver.find_element(*MainPage.exploreDeveloperHubButton).click()

    def click_add_your_dapp_button(self):
        self.driver.find_element(*MainPage.addYourDappButton).click()

    def assert_main_page_url(self):
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.url_to_be("https://neonevm.org/"))
        URL = self.driver.current_url
        print(URL)
        assert 'https://neonevm.org/' == URL, "URLs are different!"