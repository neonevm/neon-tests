from enum import Enum

from ui.pages.constants import FAQ_URL, WEBSITE_URL, TWITTER_URL, DISCORD_URL, NEONPASS_URL, DOCS_URL, COOKIES_URL


class NavigationTarget(Enum):
    FAQ = ("faq", "faq_button_click", FAQ_URL, True, "FAQ documentation")
    DOCS = ("docs", "docs_button_click", DOCS_URL, True, "Documentation")
    ABOUT_NEON = ("about_neon", "about_neon_link_button_click", WEBSITE_URL, True, "About Neon page")
    TWITTER = ("twitter", "twitter_button_click", TWITTER_URL, True, "Twitter profile")
    DISCORD = ("discord", "discord_button_click", DISCORD_URL, True, "Discord community")
    SUPPORT = ("support", "support_button_click", DISCORD_URL, True, "Support page")
    NEONPASS = ("neonpass", "neonpass_button_click", NEONPASS_URL, True, "NeonPass portal")
    COOKIES = ("cookies", "cookies_policy_link_click", COOKIES_URL, False, "Cookies policy")

    def __init__(self, test_name, method_name, expected_url, opens_new_tab, description):
        self.test_name = test_name
        self.method_name = method_name
        self.expected_url = expected_url
        self.opens_new_tab = opens_new_tab
        self.description = description
