from selenium import webdriver

from ui.pages.DeveloperPage import DeveloperPage
from ui.pages.EcosystemPage import EcosystemPage
from ui.pages.ExternalPages import ExternalPages
from ui.pages.MainPage import MainPage
from ui.pages.Menu import Menu
from utils.BaseClass import BaseClass

driver = webdriver.Chrome()
driver.implicitly_wait(10)
driver.get("https://neonevm.org/")
driver.maximize_window()

mainPage = MainPage(driver)
menuPage = Menu(driver)
developerPage = DeveloperPage(driver)
ecosystemPage = EcosystemPage(driver)
externalPages = ExternalPages(driver)
baseClass = BaseClass(driver)

class TestMainPage:

    def test_logo_header(self):
        #log = self.getLogger()
        menuPage.click_on_menu_developers_link()
        developerPage.assert_text_on_build_on_neon_block_link()
        mainPage.click_on_logo_on_header()
        mainPage.assert_main_page_url()
        driver.close()

    def test_logo_footer(self):
        #log = self.getLogger()
        menuPage.click_on_menu_developers_link()
        developerPage.assert_text_on_build_on_neon_block_link()
        mainPage.click_on_logo_on_footer()
        mainPage.assert_main_page_url()
        driver.close()

    def test_click_build_on_neon_button(self):
        #log = self.getLogger()
        mainPage.click_on_build_on_neon_button()
        developerPage.assert_developers_page_url()
        developerPage.assert_text_on_build_on_neon_block_link()
        baseClass.no_errors_on_page()
        driver.close()

    def test_click_start_building_button(self):
        #log = self.getLogger()
        mainPage.click_start_building_button()
        externalPages.assert_neon_docs_page_url()
        baseClass.no_errors_on_page()

    def test_explore_ecosystem_button(self):
        #log = self.getLogger()
        mainPage.click_explore_ecosystem_button()
        ecosystemPage.assert_ecosystem_page_url()
        ecosystemPage.assert_text_on_build_on_neon_block_link()
        baseClass.no_errors_on_page()

    def test_explore_developer_hub_button(self):
        #log = self.getLogger()
        mainPage.click_explore_developer_hub_button()
        developerPage.assert_page_url()
        developerPage.assert_text_on_build_on_neon_block_link()
        baseClass.no_errors_on_page()

    def test_add_your_dapp_button(self):
        #log = self.getLogger()
        mainPage.click_add_your_dapp_button()
        externalPages.assert_google_forms_page_url()
        externalPages.assert_text_on_googleform_title()
        baseClass.no_errors_on_page()
        driver.quit()

