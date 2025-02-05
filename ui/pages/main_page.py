import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException

from utils.base_page import BasePage


class MainPage(BasePage):
    _url = "https://neonevm.org/"

    email = "test@test.com"
    smart_contract_text = "Smart contract"

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
    audit_page = "https://neonevm.org/docs/about/why_neon#public-and-audited"
    proxy_page = "https://neonevm.org/docs/operating/operator-introduction"
    neon_architecture_page = "https://neonevm.org/docs/architecture/neon_evm_arch"

    logo_on_header = (By.XPATH, "//*[@id='header']/div[2]/div[1]")
    logo_on_footer = (By.XPATH, "(//a[@aria-label='Go to home'])[3]")
    build_on_neon_button = (By.XPATH, "//span[contains(text(),'build on neon')]")
    start_building_button = (By.XPATH, "//a[@href='https://neonevm.org/docs/'][contains(.,'Start Building')]")
    explore_ecosystem_button = (By.XPATH, "//span[@class='button__content'][contains(.,'Explore ecosystem')]")
    explore_developer_hub_button = (By.XPATH, "//span[@class='button__content'][contains(.,'Explore developer hub')]")
    add_your_dapp_button = (By.XPATH, "//span[@class='button__content'][contains(.,'add your dapp')]")
    transaction_cost_arrow = (By.XPATH, "(//div[contains(@class,'arrow-down-icon-container')])[2]")
    transaction_cost_info = (By.XPATH, "//span/p[contains(text(),'Sending ERC20')]")
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
    news_section = (By.XPATH, "//div[contains(@class,'grid-plate')]/div[contains(@class,'flex-row')]/a")
    first_news = (By.XPATH, "//div[contains(@class,'grid-plate')]/div[contains(@class,'flex-row')]/a[1]")
    security_audit_tab = (By.XPATH, "//button/span[text()='Security Audits']")
    access_security_audits_link = (By.XPATH, "//div[@role='tabpanel']//a")
    become_an_operator_tab = (By.XPATH, "//button/span[text()='Become an Operator']")
    proxy_page_link = (By.XPATH, "//div[@role='tabpanel']//a")
    accordion_element = (By.XPATH, "//div[@class='accordion-item']//span[text()='Modularity']")
    button_explore_architecture = (By.XPATH, "//span[text()='EXPLORE ARCHITECTURE']")

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
    security_audit_title = (By.XPATH, "//div[@role='tabpanel']//h4[text()='Security Audits']")
    become_an_operator_title = (By.XPATH, "//div[@role='tabpanel']//h4[text()='Become an Operator']")

    @allure.step("Click on the logotype on header")
    def click_on_logo_on_header(self):
        self.wait.until(EC.presence_of_element_located(MainPage.logo_on_header)).click()

    @allure.step("Click on the logotype on footer")
    def click_on_logo_on_footer(self):
        self.wait.until(EC.presence_of_element_located(MainPage.logo_on_footer)).click()

    @allure.step("Click 'Build on Neon' button")
    def click_on_build_on_neon_button(self, max_attempts=3):
        attempts = 0
        while attempts < max_attempts:

            self.wait.until(EC.visibility_of_element_located(MainPage.build_on_neon_button)).click()

            try:
                WebDriverWait(self.driver, 5).until(lambda driver: len(driver.window_handles) > 1)
                return
            except TimeoutException:
                attempts += 1
        raise Exception("Can't open new tab")

    @allure.step("Click 'Start Building' button")
    def click_start_building_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.start_building_button)).click()

    @allure.step("Click 'Explore Ecosystem' button")
    def click_explore_ecosystem_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.explore_ecosystem_button)).click()

    @allure.step("Click 'Explore developer hub' button")
    def click_explore_developer_hub_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.explore_developer_hub_button)).click()

    @allure.step("Click 'Add your dapp' button")
    def click_add_your_dapp_button(self):
        self.wait.until(EC.presence_of_element_located(MainPage.add_your_dapp_button)).click()

    @allure.step("Input email")
    def input_email(self):
        email_field = self.wait.until(EC.visibility_of_element_located(MainPage.email_input_field))
        email_field.send_keys(MainPage.email)

    @allure.step("Check message, that user already subscribed, is visible")
    def check_already_subscribed_text(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.subscription_notification_text)).is_displayed()

    @allure.step("Click 'Ask me later' button")
    def click_ask_me_later_button(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.ask_me_later_button)).click()

    @allure.step("Click 'Accept' button")
    def click_accept_button(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.accept_button)).click()

    @allure.step("Check the banner with cookies info is not exists")
    def assert_cookie_banner_is_invisible(self):
        self.wait.until(EC.invisibility_of_element(MainPage.cookie_banner))

    @allure.step("Check the banner with cookies info exists")
    def assert_cookie_banner_is_visible(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.cookie_banner)).is_displayed()

    @allure.step("Click on the 'Subscribe' button")
    def click_subscribe_button(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.subscribe_button)).click()

    @allure.step("Click on the social network icon")
    def click_social_network_icon(self, icon_name):
        self.wait.until(EC.visibility_of_element_located(icon_name)).click()

    @allure.step("Click on the Terms of use link")
    def click_terms_of_use_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.terms_of_use_link)).click()

    @allure.step("Click on the Disclaimer link")
    def click_disclaimer_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.disclaimer_link)).click()

    @allure.step("Click on the Cookie Policy link")
    def click_cookie_policy_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.cookie_policy_link)).click()

    @allure.step("Click on the Privacy Policy link")
    def click_privacy_policy_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.privacy_policy_link)).click()

    @allure.step("Check page title")
    def check_page_title(self, page_title):
        self.wait.until(EC.visibility_of_element_located(page_title)).is_displayed()

    @allure.step("Check count of news on the page")
    def check_news_section(self, count: int):
        news_count = len(self.wait.until(EC.visibility_of_all_elements_located(MainPage.news_section)))
        assert news_count == count, f"Number of news is {news_count}"

    @allure.step("Click on the first news in the list")
    def redirect_to_news_page(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.first_news)).click()

    @allure.step("Click 'Security audits' tab")
    def security_audit_tab_click(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.security_audit_tab)).click()

    @allure.step("Check 'Security audits' title is visible")
    def check_security_audit_title(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.security_audit_title)).is_displayed()

    @allure.step("Click 'Access security audits' button")
    def click_access_audit_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.access_security_audits_link)).click()

    @allure.step("Click 'Become an Operator' tab")
    def become_an_operator_tab_click(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.become_an_operator_tab)).click()

    @allure.step("Check 'Become an Operator' title is visible")
    def check_become_an_operator_title(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.become_an_operator_title)).is_displayed()

    @allure.step("Click 'Proxy technical docs' button")
    def click_proxy_technical_docs_link(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.proxy_page_link)).click()

    @allure.step("Click accordion element 'Modularity'")
    def click_accordion_element(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.accordion_element)).click()

    @allure.step("Check 'Explore Architecture' button is visible")
    def check_accordion_element_text_is_visible(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.button_explore_architecture)).is_displayed()

    @allure.step("Check 'Explore Architecture' button is invisible")
    def check_accordion_element_text_is_invisible(self):
        self.wait.until(EC.invisibility_of_element(MainPage.button_explore_architecture))

    @allure.step("Click 'Explore Architecture' button")
    def explore_architecture_button_click(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.button_explore_architecture)).click()

    @allure.step("Check transaction cost arrow chandes color while hover")
    def transaction_element_change_color(self, max_attempts=3):
        element = self.wait.until(EC.visibility_of_element_located(MainPage.transaction_cost_arrow))
        original_color = element.value_of_css_property("color")
        self.scroll_page_to_element(element)

        for attempt in range(max_attempts):
            self.hover_element(element)

            try:
                WebDriverWait(self.driver, 2).until(
                    lambda driver: element.value_of_css_property("color") != original_color
                )
                return
            except TimeoutException:
                continue
        raise Exception("Color stays the same")

    @allure.step("Click transaction cost arrow")
    def click_transaction_element(self):
        self.wait.until(EC.visibility_of_element_located(MainPage.transaction_cost_arrow)).click()

    @allure.step("Check transaction cost dropdown contains text 'Smart contract'")
    def assert_transaction_text(self):
        element = self.wait.until(EC.presence_of_element_located(MainPage.transaction_cost_info))
        assert MainPage.smart_contract_text in element.text, f"Text {MainPage.smart_contract_text} not found"
