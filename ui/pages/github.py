from . import BasePage


class GithubAuthPage(BasePage):
    authorized = False

    def page_loaded(self):
        url = self.page.url
        if "github.com/login/oauth/authorize" in url:
            self.authorized = True
            self.page.wait_for_selector("text='Authorizing will redirect to'", timeout=10000)
        else:
            self.page.wait_for_selector('a[href="https://github.com/contact"]', timeout=10000)

    @property
    def username(self):
        return self.page.query_selector('input[name="login"]')

    @property
    def password(self):
        return self.page.query_selector('input[name="password"]')

    @property
    def submit(self):
        return self.page.query_selector('input[name="commit"]')

    @property
    def authorize_user_button(self):
        return self.page.query_selector('//button[starts-with(text(), "Authorize")]')
