from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from utils.base_page import BasePage


class MainPage(BasePage):
    _url = "https://neonevm.org/"

    email = "test@test.com"

    twitter_page = "https://x.com/Neon_EVM?mx=2"
    github_page = "https://github.com/neonevm/neon-evm"
    discord_page = "https://discord.com/invite/neonevm"
    medium_page = "https://medium.com/@neon_evm"
    telegram_page = "https://t.me/NeonEvmCommunity"
    linkedin_page = "https://www.linkedin.com/company/neonevm/"
    terms_page = "https://neonevm.org/terms"
    cookie_page = "https://neonevm.org/cookie-policy"
    disclaimer_page = "https://neonevm.org/disclaimer"
    privacy_page = "https://neonevm.org/privacy-policy"

    logo_on_header = (By.XPATH, "//*[@id='header']/div[2]/div[1]")
    logo_on_footer = (By.XPATH, "(//a[@aria-label='Go to home'])[3]")
    build_on_neon_button = (By.XPATH, "//span[contains(text(),'build on neon')]")
    start_building_button = (By.XPATH, "//a[@href='https://neonevm.org/docs/'][contains(.,'Start Building')]")
    explore_ecosystem_button = (By.XPATH, "//span[@class='button__content'][contains(.,'Explore ecosystem')]")
    explore_developer_hub_button = (By.XPATH, "//span[@class='button__content'][contains(.,'Explore developer hub')]")
    add_your_dapp_button = (By.XPATH, "//span[@class='button__content'][contains(.,'add your dapp')]")
    transaction_cost_arrow = (By.XPATH, "(//div[contains(@class,'arrow-down-icon-container')])[2]")
    email_input_field = (By.XPATH, "//input")
    subscribe_button = (By.XPATH, "//button/span[text()='subscribe']")
    subscription_notification_text = (By.XPATH, "//div[contains(text(), 'already subscribed')]")
    cookie_banner = (By.XPATH, "//h4[contains(text(), 'We use cookies')]")
    ask_me_later_button = (By.XPATH, "//button[text()='ASK ME LATER']")
    accept_button = (By.XPATH, "//button[text()='ACCEPT']")
    terms_of_use_link = (By.XPATH, "//a[contains(text(),'Terms Of Use')]")
    cookie_policy_link = (By.XPATH, "//a[contains(text(),'Cookie Policy')]")
    disclaimer_link = (By.XPATH, "//a[contains(text(),'Disclaimer')]")
    privacy_policy_link = (By.XPATH, "//a[contains(text(),'Privacy')]")

    twitter_icon = (By.XPATH, "//a[@title='twitter']")
    githib_icon = (By.XPATH, "//a[@title='github']")
    discord_icon = (By.XPATH, "//a[@title='discord']")
    medium_icon = (By.XPATH, "//a[@title='medium']")
    telegram_icon = (By.XPATH, "//a[@title='telegram']")
    linkedin_icon = (By.XPATH, "//a[@title='linkedin']")
    terms_of_use_page_title = (By.XPATH, "//h1[contains(text(),'Terms of Use')]")
    disclaimer_page_title = (By.XPATH, "//h1[contains(text(),'Disclaimer')]")
    privacy_policy_page_title = (By.XPATH, "//h1[contains(text(),'Privacy')]")
    cookie_policy_page_title = (By.XPATH, "//h1[contains(text(),'Cookie Policy')]")

    def click_on_logo_on_header(self):
        self.wait.until(EC.presence_of_element_located(MainPage.logo_on_header)).click()

    def click_on_logo_on_footer(self):
        self.wait.until(EC.presence_of_element_located(MainPage.logo_on_footer)).click()

    def click_on_build_on_neon_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.build_on_neon_button)).click()

    def click_start_building_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.start_building_button)).click()

    def click_explore_ecosystem_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.explore_ecosystem_button)).click()

    def click_explore_developer_hub_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.explore_developer_hub_button)).click()

    def click_add_your_dapp_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.add_your_dapp_button)).click()

    def input_email(self):
        email_field = self.wait.until(EC.visibility_of_element_located(MainPage.email_input_field))
        email_field.send_keys(MainPage.email)

    def click_subscribe_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.subscribe_button)).click()

    def check_already_subscribed_text(self):
        self.wait.until(EC.presence_of_element_located(MainPage.subscription_notification_text)).is_displayed()

    def click_social_network_icon(self, icon_name):
        self.wait.until(EC.visibility_of_element_located(icon_name)).click()

    def click_ask_me_later_button(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.ask_me_later_button)).click()

    def click_accept_button(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.accept_button)).click()

    def assert_cookie_banner_is_invisible(self):
        self.wait.until(EC.invisibility_of_element(MainPage.cookie_banner))

    def assert_cookie_banner_is_visible(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.cookie_banner))

    def click_subscribe_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.subscribe_button)).click()

    def click_social_network_icon(self, icon_name):
        self.wait.until(EC.visibility_of_element_located(icon_name)).click()

    def click_ask_me_later_button(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.ask_me_later_button)).click()

    def click_accept_button(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.accept_button)).click()

    def assert_cookie_banner_is_invisible(self):
        self.wait.until(EC.invisibility_of_element(MainPage.cookie_banner))

    def assert_cookie_banner_is_visible(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.cookie_banner)).is_displayed()

    def click_terms_of_use_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.terms_of_use_link)).click()

    def click_disclaimer_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.disclaimer_link)).click()

    def click_cookie_policy_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.cookie_policy_link)).click()

    def click_privacy_policy_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.privacy_policy_link)).click()

    def check_page_title(self, page_title):
        self.wait.until(EC.visibility_of_element_located(page_title))
