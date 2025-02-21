class TestMainPage:

    def test_logo_header(self, main_page, menu_page, developers_page):
        menu_page.click_on_menu_developers_start_building_link()
        developers_page.assert_text_on_build_on_neon_block_link()
        main_page.click_on_logo_on_header()
        main_page.assert_page_url()

    def test_logo_footer(self, main_page, menu_page, developers_page):
        menu_page.click_on_menu_developers_start_building_link()
        developers_page.assert_text_on_build_on_neon_block_link()
        main_page.click_on_logo_on_footer()
        main_page.assert_page_url()

    def test_click_start_building_button(self, main_page, menu_page, developers_page):
        main_page.click_start_building_button()
        main_page.switch_window(1)
        main_page.assert_windows_count(2)
        developers_page.assert_page_url()
        developers_page.assert_text_on_build_on_neon_block_link()

    def test_click_technical_docs_button(self, main_page, quick_start_page):
        main_page.click_technical_docs_button()
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
        email = "test@test.com"
        main_page.input_email(email)
        main_page.click_subscribe_button()
        main_page.check_already_subscribed_text()

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

    def test_check_terms_of_use_page(self, main_page):
        main_page.click_terms_of_use_link()
        main_page.assert_page_url(url=main_page.terms_page)
        main_page.check_page_title(main_page.terms_of_use_page_title)

    def test_check_disclaimer_page(self, main_page):
        main_page.click_disclaimer_link()
        main_page.assert_page_url(url=main_page.disclaimer_page)
        main_page.check_page_title(main_page.disclaimer_page_title)

    def test_check_privacy_policy_page(self, main_page):
        main_page.click_privacy_policy_link()
        main_page.assert_page_url(url=main_page.privacy_page)
        main_page.check_page_title(main_page.privacy_policy_page_title)

    def test_check_cookie_page(self, main_page):
        main_page.click_cookie_policy_link()
        main_page.assert_page_url(url=main_page.cookie_page)
        main_page.check_page_title(main_page.cookie_policy_page_title)

    def test_check_news_section(self, main_page, blog_page):
        main_page.check_news_section(3)
        main_page.redirect_to_news_page()
        main_page.assert_partial_matching_url(url="/blog/")
        blog_page.assert_post_not_empty()

    def test_security_audits_tab(self, main_page):
        main_page.security_audit_tab_click()
        main_page.check_security_audit_title()
        main_page.click_access_audit_link()
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.audit_page)

    def test_become_an_operator_tab(self, main_page):
        main_page.security_audit_tab_click()
        main_page.become_an_operator_tab_click()
        main_page.check_become_an_operator_title()
        main_page.click_proxy_technical_docs_link()
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.proxy_page)

    def test_accrodion_element_is_hiding(self, main_page):
        main_page.click_accordion_element()
        main_page.check_accordion_element_text_is_visible()
        main_page.click_accordion_element()
        main_page.check_accordion_element_text_is_invisible()

    def test_click_link_on_accrodion_element(self, main_page):
        main_page.click_accordion_element()
        main_page.check_accordion_element_text_is_visible()
        main_page.explore_architecture_button_click()
        main_page.switch_window(1)
        main_page.assert_page_url(url=main_page.neon_architecture_page)

    def test_check_transaction_data(self, main_page):
        main_page.transaction_element_change_color()
        main_page.click_transaction_element()
        main_page.assert_transaction_text()

    def test_menu_link_to_pdf_docs(self, menu_page):
        menu_page.click_on_menu_developers_link()
        menu_page.click_on_solana_link()
        menu_page.switch_window(1)
        menu_page.assert_page_url(url=menu_page.solana_pdf)

    def test_menu_link_to_external_pages(self, menu_page):
        menu_page.click_on_menu_ecosystem_link()
        menu_page.click_on_neonpass_link()
        menu_page.switch_window(1)
        menu_page.assert_page_url(url=menu_page.neonpass)

    def test_menu_link_to_internal_pages(self, menu_page):
        menu_page.click_on_menu_news_link()
        menu_page.click_on_events_link()
        menu_page.assert_page_url(url=menu_page.events)
