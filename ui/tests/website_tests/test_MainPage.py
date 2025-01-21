from ui.tests.website_tests.conftest import (
    google_forms_page,
    menu_page,
    developers_page,
    main_page,
    ecosystem_page,
    quick_start_page,
)

class TestMainPage:
    def test_logo_header(self, main_page, menu_page, developers_page):
        menu_page.click_on_menu_developers_link()
        developers_page.assert_text_on_build_on_neon_block_link()
        main_page.click_on_logo_on_header()
        main_page.assert_page_url()

    def test_logo_footer(self, main_page, menu_page, developers_page):
        menu_page.click_on_menu_developers_link()
        developers_page.assert_text_on_build_on_neon_block_link()
        main_page.click_on_logo_on_footer()
        main_page.assert_page_url()

    def test_click_build_on_neon_button(self, main_page, menu_page, developers_page):
        main_page.click_on_build_on_neon_button()
        main_page.switch_window(1)
        main_page.assert_windows_count(2)
        developers_page.assert_page_url()
        developers_page.assert_text_on_build_on_neon_block_link()

    def test_click_start_building_button(self, main_page, quick_start_page):
        main_page.click_start_building_button()
        main_page.switch_window(1)
        main_page.assert_windows_count(2)
        quick_start_page.assert_page_url()
        quick_start_page.assert_text_on_quick_start_page_title()

    def test_explore_ecosystem_button(self, main_page, ecosystem_page):
        main_page.click_explore_ecosystem_button()
        ecosystem_page.assert_page_url()
        ecosystem_page.assert_text_on_build_on_neon_block_link()

    def test_explore_developer_hub_button(self, main_page, developers_page):
        main_page.click_explore_developer_hub_button()
        developers_page.assert_page_url()
        developers_page.assert_text_on_build_on_neon_block_link()

    def test_add_your_dapp_button(self, main_page, google_forms_page):
        main_page.click_add_your_dapp_button()
        main_page.switch_window(1)
        main_page.assert_windows_count(2)
        google_forms_page.assert_page_url()
        google_forms_page.assert_text_on_googleform_title()

    def test_check_subscription(self, main_page):
        main_page.input_email()
        main_page.click_subscribe_button()

    def test_check_twitter_page(self, main_page):
        main_page.click_social_network_icon(icon_name=main_page.twitter_icon)
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.twitter_page)

    def test_check_github_page(self, main_page):
        main_page.click_social_network_icon(icon_name=main_page.githib_icon)
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.github_page)

    def test_check_discord_page(self, main_page):
        main_page.click_social_network_icon(icon_name=main_page.discord_icon)
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.discord_page)

    def test_check_medium_page(self, main_page):
        main_page.click_social_network_icon(icon_name=main_page.medium_icon)
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.medium_page)

    def test_check_telegram_page(self, main_page):
        main_page.click_social_network_icon(icon_name=main_page.telegram_icon)
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.telegram_page)

    def test_check_linkedin_page(self, main_page):
        main_page.click_social_network_icon(icon_name=main_page.linkedin_icon)
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.linkedin_page)

    def test_close_cookie_banner(self, main_page):
        main_page.click_ask_me_later_button()
        main_page.assert_cookie_banner_is_invisible()
        main_page.clear_local_storage()
        main_page.reload_page()
        main_page.assert_cookie_banner_is_visible()

    def test_accept_cookie(self, main_page):
        main_page.assert_cookie_banner_is_visible()
        main_page.click_accept_button()
        main_page.reload_page()
        main_page.assert_cookie_banner_is_invisible()
