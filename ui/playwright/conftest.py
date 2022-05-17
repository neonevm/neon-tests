import pathlib
import typing as tp
from datetime import datetime

import allure
import pytest
from playwright.sync_api import BrowserContext
from playwright.sync_api import Page

from ui.libs import get_config
from ui.pages import login

pytest_plugins = ["ui.plugins.browser"]


@pytest.fixture(scope="session")
def scalr_users() -> tp.Dict[str, tp.Dict[str, str]]:
    return get_config("surefire/container.json")


@pytest.fixture
def scalr_login_page(context: BrowserContext, page: Page) -> login.LoginPage:
    """Return scalr login page without authorization"""
    context.clear_cookies()
    page.goto("/")
    return login.LoginPage(page)


@pytest.fixture(autouse=True)
def save_screenshot_on_fail(request: pytest.FixtureRequest, page: Page):
    fail_count = request.session.testsfailed
    yield
    if request.session.testsfailed > fail_count:
        file_path = (
            pathlib.Path("/tmp") / f"{datetime.now().strftime('%Y%M%D-%h:%m:%s')}.png"
        ).as_posix()
        page.screenshot(path=file_path, full_page=True)
        allure.attach.file(
            file_path,
            name="fail_screenshot",
            attachment_type=allure.attachment_type.PNG,
            extension="png",
        )


# placeholder for invite_new_user test
def pytest_configure():
    pytest.user = None
