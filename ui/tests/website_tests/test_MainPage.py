from ui.pages.developer_page import DeveloperPage
from ui.tests.website_tests.conftest import external_pages, base_class, menu_page, developers_page, main_page, ecosystem_page
from selenium.webdriver.support.wait import WebDriverWait

class TestMainPage:

    def test_logo_header(self, main_page, menu_page, developers_page):
        menu_page.click_on_menu_developers_link()
        developers_page.assert_text_on_build_on_neon_block_link()
        main_page.click_on_logo_on_header()
        main_page.assert_page_url()

    def test_logo_footer(self,main_page, menu_page, developers_page):
        menu_page.click_on_menu_developers_link()
        developers_page.assert_text_on_build_on_neon_block_link()
        main_page.click_on_logo_on_footer()
        main_page.assert_main_page_url()

    def test_click_build_on_neon_button(self, main_page, menu_page, developers_page, base_class):
        main_page.click_on_build_on_neon_button()
        developers_page.assert_developers_page_url()
        developers_page.assert_text_on_build_on_neon_block_link()
        base_class.no_errors_on_page()

    def test_click_start_building_button(self, main_page, external_pages, base_class):
        main_page.click_start_building_button()
        external_pages.assert_neon_docs_page_url()
        base_class.no_errors_on_page()

    def test_explore_ecosystem_button(self, main_page, ecosystem_page, base_class):
        main_page.click_explore_ecosystem_button()
        ecosystem_page.assert_ecosystem_page_url()
        ecosystem_page.assert_text_on_build_on_neon_block_link()
        base_class.no_errors_on_page()

    def test_explore_developer_hub_button(self, main_page, developers_page, base_class):
        main_page.click_explore_developer_hub_button()
        base_class.assert_page_url(developers_page.developers_url)
        developers_page.assert_text_on_build_on_neon_block_link()
        base_class.no_errors_on_page()

    def test_add_your_dapp_button(self, main_page, external_pages, base_class):
        main_page.click_add_your_dapp_button()
        external_pages.assert_google_forms_page_url()
        external_pages.assert_text_on_googleform_title()
        base_class.no_errors_on_page()