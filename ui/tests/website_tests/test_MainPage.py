from ui.tests.website_tests.conftest import google_forms_page, base_class, menu_page, developers_page, main_page, \
    ecosystem_page, quick_start_page, github_page


class TestMainPage:

    def test_logo_header(self, main_page, menu_page, developers_page,base_class):
        menu_page.click_on_menu_developers_link()
        developers_page.assert_text_on_build_on_neon_block_link()
        main_page.click_on_logo_on_header()
        base_class.assert_page_url(url=main_page._url)

    def test_logo_footer(self,main_page, menu_page, developers_page,base_class):
        menu_page.click_on_menu_developers_link()
        developers_page.assert_text_on_build_on_neon_block_link()
        main_page.click_on_logo_on_footer()
        base_class.assert_page_url(url=main_page._url)

    def test_click_build_on_neon_button(self, main_page, menu_page, developers_page, base_class):
        main_page.click_on_build_on_neon_button()
        base_class.switch_window(1)
        base_class.assert_page_url(url=developers_page._url)
        developers_page.assert_text_on_build_on_neon_block_link()

    def test_click_start_building_button(self, main_page, base_class, quick_start_page):
        main_page.click_start_building_button()
        base_class.switch_window(1)
        base_class.assert_page_url(url=quick_start_page._url)
        quick_start_page.assert_text_on_quick_start_page_title()

    def test_explore_ecosystem_button(self, main_page, ecosystem_page, base_class):
        main_page.click_explore_ecosystem_button()
        base_class.assert_page_url(url=ecosystem_page._url)
        ecosystem_page.assert_text_on_build_on_neon_block_link()

    def test_explore_developer_hub_button(self, main_page, developers_page, base_class):
        main_page.click_explore_developer_hub_button()
        base_class.assert_page_url(url=developers_page._url)
        developers_page.assert_text_on_build_on_neon_block_link()

    def test_add_your_dapp_button(self, main_page, google_forms_page, base_class):
        main_page.click_add_your_dapp_button()
        base_class.switch_window(1)
        base_class.assert_page_url(url=google_forms_page._url)
        google_forms_page.assert_text_on_googleform_title()