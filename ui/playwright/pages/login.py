import time

from . import BasePage
from .environment_scope import EnvironmentDashboard
from .sign_up import SignUpPageStepOne


class LoginPage(BasePage):
    def page_loaded(self):
        self.page.wait_for_selector("text='Sign in'", state="visible", timeout=30000)

    def select_idp(self, idp: str):
        self.page.click("div.x-form-trigger")
        self.page.click(f"text={idp}")

    def set_email(self, email: str):
        self.page.hover('input[name="scalrLogin"]', timeout=3000)
        self.page.fill('input[name="scalrLogin"]', email, timeout=3000)

    def set_password(self, password: str):
        self.page.hover('input[name="scalrPass"]', timeout=3000)
        self.page.fill('input[name="scalrPass"]', password, timeout=3000)

    def login(self, first_login=False, failed_login=False):
        login_selector = "xpath=//span[contains(text(), 'Login')]/ancestor::a[not(contains(@style,'display: none'))]"
        self.page.hover(selector=login_selector, timeout=3000)
        self.page.click(selector=login_selector, timeout=3000)
        if any([first_login, failed_login]):  # modal window processing will be raised
            self.page.is_visible('text="Processing..."')
            self.page.wait_for_selector('text="Processing..."', state="hidden")
        else:
            self.page.is_visible('text="Loading page..."')
            self.page.wait_for_selector('text="Loading page..."', state="hidden")
        if failed_login:
            return LoginPage(self.page)
        return ChangePasswordPopUp(self.page) if first_login else EnvironmentDashboard(self.page)

    def forgot_password_open(self) -> None:
        self.page.click("text='Forgot your password?'")
        self.page.wait_for_selector("text='Recover password'", state="visible", timeout=5000)

    def sign_up(self) -> SignUpPageStepOne:
        self.page.query_selector("a[href='#/public/signup']").click()
        self.page.is_visible('text="Loading page..."')
        self.page.wait_for_selector('text="Loading page..."', state="hidden")
        return SignUpPageStepOne(self.page)


class SignInTo(LoginPage):
    def page_loaded(self):
        self.page.wait_for_selector("text='Sign in to '", state="visible", timeout=30000)


class ChangePasswordPopUp(BasePage):

    _pop_up_root_selector = (
        "//div[@role='form' and starts-with(@id, 'form-') "
        "and starts-with(@class, 'x-panel-body')]"
    )

    def page_loaded(self):
        self.page.wait_for_selector(
            f"{self._pop_up_root_selector}//ancestor::div//div[contains(text(), 'New password')]",
            state="visible",
            timeout=30000,
        )

    @property
    def email(self):
        return self.page.text_content(
            selector=f"{self._pop_up_root_selector}//div[starts-with(@id, 'displayfield') "
            f"and starts-with(@class, 'x-form-item-body')]/div",
            timeout=500,
        )

    def fill_new_password(self, password: str):
        input_selector = (
            f"{self._pop_up_root_selector}//div[starts-with(@id, 'scalrpasswordfield')]//input"
        )
        self.page.hover(selector=input_selector, timeout=500)
        self.page.fill(selector=input_selector, timeout=3000, value=password)

    def confirm_new_password(self, password: str):
        input_selector = f"{self._pop_up_root_selector}//div[starts-with(@id, 'textfield')]//input"
        self.page.hover(selector=input_selector, timeout=500)
        self.page.fill(selector=input_selector, timeout=3000, value=password)

    def update_new_password(self):
        bttn_selector = (
            f"{self._pop_up_root_selector}" f"//ancestor::div//a//span[text()='Update my password']"
        )
        self.page.hover(selector=bttn_selector, timeout=3000)
        self.page.click(selector=bttn_selector, timeout=3000)
        # TODO https://scalr-labs.atlassian.net/browse/SCALRCORE-20439
        time.sleep(2)
        return SignInTo(self.page)

    def cancel(self):
        bttn_selector = f"{self._pop_up_root_selector}" f"//ancestor::div//a//span[text()='Cancel']"
        self.page.hover(selector=bttn_selector, timeout=3000)
        self.page.click(selector=bttn_selector, timeout=3000)
        return SignInTo(self.page)
