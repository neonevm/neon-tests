from . import BasePage
from .workspaces import NewWorkspacePage


class SignUpPageStepOne(BasePage):

    """
    The step in which we enter the email address to which the verification code or invitation link will come
    """

    def page_loaded(self) -> None:
        self.page.wait_for_selector(
            "//div[contains(text(), 'Sign up')]", state="visible", timeout=30000
        )

    def set_email(self, email: str) -> None:
        self.page.fill(
            "//div[starts-with(@id, 'signup-step1-')"
            " and @data-ref='body']//input[@name='email']",
            email,
            timeout=500,
        )

    def click_continue(self):
        bttn_continue = "//div[starts-with(@id, 'signup-step1-')]//span[text()='continue']"
        self.page.hover(selector=bttn_continue, timeout=3000)
        self.page.click(selector=bttn_continue, timeout=3000)
        return SignUpPageStepTwo(self.page)

    def error_tooltip(self) -> str:
        error_placeholder = "//div[starts-with(@id, 'signup-step1-')]//li"
        self.page.wait_for_selector(selector=error_placeholder, timeout=3000)
        return self.page.inner_text(selector=error_placeholder, timeout=500)


class SignUpPageStepTwo(BasePage):

    """
    Step in which we will enter the verification code
    (in the case of the invitation link, we will go immediately to step 3)
    """

    def page_loaded(self) -> None:
        # button resend is unique on this sub-step
        self.page.wait_for_selector(
            "//div[starts-with(@id, 'signup-step2-')]//span[text()='resend code']", timeout=30000
        )

    def click_continue(self):
        bttn_continue = "//div[starts-with(@id, 'signup-step2-')]//span[text()='continue']"
        self.page.hover(selector=bttn_continue, timeout=3000)
        self.page.click(selector=bttn_continue, timeout=3000)
        return SignUpPageStepThree(self.page)

    def click_resend_code(self) -> None:
        resend_code_bttn = "//div[starts-with(@id, 'signup-step2-')]//span[text()='resend code']"
        self.page.hover(selector=resend_code_bttn, timeout=3000)
        self.page.click(selector=resend_code_bttn, timeout=3000)

    def go_back_to_the_first_step(self):
        bttn_back = "//div[starts-with(@id, 'signup-step2-')]//span[text()='back']"
        self.page.hover(selector=bttn_back, timeout=3000)
        self.page.click(selector=bttn_back, timeout=3000)
        return SignUpPageStepOne(self.page)

    def fill_the_verification_code(self, code: list) -> None:
        inputs = self.page.query_selector_all(
            selector="//div[starts-with(@id, 'signup-step2-')]"
            "//div[starts-with(@id, 'verificationCode')]//input"
        )
        for inp, val in zip(inputs, code):
            inp.hover()
            inp.click()
            inp.fill(val, timeout=500)

    def error_tooltip(self) -> str:
        error_placeholder = "//div[starts-with(@id, 'signup-step2-')]//li"
        self.page.wait_for_selector(selector=error_placeholder, timeout=3000)
        return self.page.inner_text(selector=error_placeholder, timeout=500)


class SignUpPageStepThree(BasePage):

    """
    The step in which we enter the company name, which will be our entry point to the company dashboard.
    """

    def page_loaded(self) -> None:
        self.page.wait_for_selector(
            "//div[starts-with(@id, 'signup-step3-') and @data-ref='body']//input[@name='accountName']",
            state="visible",
            timeout=30000,
        )

    def click_continue(self):
        bttn_continue = "//div[starts-with(@id, 'signup-step3-')]//span[text()='continue']"
        self.page.hover(selector=bttn_continue, timeout=3000)
        self.page.click(selector=bttn_continue, timeout=3000)
        return NewWorkspacePage(self.page)

    def go_back_to_the_second_step(self):
        bttn_back = "//div[starts-with(@id, 'signup-step3-')]//span[text()='back']"
        self.page.hover(selector=bttn_back, timeout=3000)
        self.page.click(selector=bttn_back, timeout=3000)
        return SignUpPageStepTwo(self.page)

    def fill_company_name(self, company_name: str) -> None:
        self.page.fill(
            "//div[starts-with(@id, 'signup-step3-') and @data-ref='body']//input[@name='accountName']",
            company_name,
            timeout=500,
        )
