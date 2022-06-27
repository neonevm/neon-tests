import os
import pathlib
import typing as tp
from datetime import datetime

import allure
import pytest
from _pytest.config import Config
from playwright.sync_api import Page

from ui import libs

EVM_NETWORKS = {
    "night-stand": "NEON EVM night-stand",
    "devnet": "NeonEVM DevNet",
}


CHROME_EXT_DIR = "extensions/chrome/plugins"
"""Relative path to Chrome extension source
"""

CHROME_USER_DATA_DIR = "user_data"
"""Relative path to Chrome extensions user data
"""


def pytest_addoption(parser):
    parser.addoption("--network", action="store", default="devnet", help="Which stand use")


@pytest.fixture(scope="session")
def network(pytestconfig: tp.Any) -> tp.Optional[str]:
    return EVM_NETWORKS.get(pytestconfig.getoption("--network"), EVM_NETWORKS["devnet"])


@pytest.fixture(scope="session")
def chrome_extensions_path(required_extensions: tp.Union[tp.List, str]) -> pathlib.Path:
    path = ""
    if isinstance(required_extensions, str):
        required_extensions = [required_extensions]
    for ext in required_extensions:
        source = pathlib.Path(__file__).parent / CHROME_EXT_DIR / ext
        if not path:
            path = source
        else:
            path = path / f",{source}"
    return path


@pytest.fixture(scope="session", autouse=True)
def chrome_extension_user_data() -> pathlib.Path:
    """Path to Chrome extension user data"""
    path = (pathlib.Path(__file__).absolute().parent / CHROME_EXT_DIR).parent / CHROME_USER_DATA_DIR
    user_data = libs.clone_user_data(path)
    yield user_data
    libs.rm_tree(user_data)


@pytest.fixture(scope="session")
def chrome_extension_password() -> str:
    """Chrome extensions password `1234Neon5678`"""
    try:
        return os.environ["CHROME_EXT_PASSWORD"]
    except KeyError:
        raise AssertionError("Please set the `CHROME_EXT_PASSWORD` environment variable (password for wallets).")


@pytest.fixture
def use_persistent_context() -> bool:
    """Flag used for Chrome extensions load, set to False for standard pages not extensions"""
    return True


@pytest.fixture
def save_screenshot_on_fail(request: pytest.FixtureRequest, page: Page):
    fail_count = request.session.testsfailed
    yield
    if request.session.testsfailed > fail_count:
        file_path = (pathlib.Path("/tmp") / f"{datetime.now().strftime('%Y%M%D-%h:%m:%s')}.png").as_posix()
        page.screenshot(path=file_path, full_page=True)
        allure.attach.file(
            file_path,
            name="fail_screenshot",
            attachment_type=allure.attachment_type.PNG,
            extension="png",
        )


def pytest_generate_tests(metafunc: tp.Any) -> None:
    if "browser_name" in metafunc.fixturenames:
        browsers = metafunc.config.option.browser or ["chrome"]
        for browser in browsers:
            if browser not in ["chrome", "chromium", "firefox", "webkit"]:
                raise ValueError(
                    f"'{browser}' is not allowed. Only chromium, firefox, or webkit are valid browser names."
                )
        metafunc.parametrize("browser_name", browsers, scope="session")


def pytest_configure(config: Config) -> None:
    config.addinivalue_line("markers", "skip_browser(name): mark test to be skipped a specific browser")
    config.addinivalue_line("markers", "only_browser(name): mark test to run only on a specific browser")


def _get_skiplist(item: tp.Any, values: tp.List[str], value_name: str) -> tp.List[str]:
    skipped_values: tp.List[str] = []
    # Allowlist
    only_marker = item.get_closest_marker(f"only_{value_name}")
    if only_marker:
        skipped_values = values
        skipped_values.remove(only_marker.args[0])

    # Denylist
    skip_marker = item.get_closest_marker(f"skip_{value_name}")
    if skip_marker:
        skipped_values.append(skip_marker.args[0])

    return skipped_values


def pytest_runtest_setup(item: tp.Any) -> None:
    if not hasattr(item, "callspec"):
        return
    browser_name = item.callspec.params.get("browser_name")
    if not browser_name:
        return

    skip_browsers_names = _get_skiplist(item, ["chrome", "chromium", "firefox", "webkit"], "browser")

    if browser_name in skip_browsers_names:
        pytest.skip("skipped for this browser: {}".format(browser_name))
