class TestFaucet:

    def test_neon_website_button(self, faucet_page):
        faucet_page.click_neon_website_button()
        faucet_page.switch_window(1)
        faucet_page.assert_windows_count(2)
        faucet_page.assert_page_url(url=faucet_page.neon_website_url)

    def test_neonpass_button(self, faucet_page):
        faucet_page.click_neonpass_button()
        faucet_page.switch_window(1)
        faucet_page.assert_windows_count(2)
        faucet_page.assert_page_url(url=faucet_page.neonpass_url)

    def test_help_button(self, faucet_page):
        faucet_page.click_help_button()
        faucet_page.switch_window(1)
        faucet_page.assert_windows_count(2)
        faucet_page.assert_page_url(url=faucet_page.faucet_docs_url)
