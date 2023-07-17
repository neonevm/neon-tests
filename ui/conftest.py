import os
import pathlib
import typing as tp
import uuid

import allure
import pytest
from _pytest.config import Config
from playwright.sync_api import Page

from ui import libs

PLATFORM_NETWORKS = {
    "night-stand": "NEON EVM night-stand",
    "devnet": "NeonEVM DevNet",
}

CHROME_TAR_PATH = pathlib.Path(__file__).absolute().parent / "extensions" / "data"
CHROME_DATA_PATH = (
    pathlib.Path(__file__).absolute().parent.parent / "chrome-data" / uuid.uuid4().hex
)
"""CHROME_DATA_PATH is temporary local destination in project to untar chrome data directory and plugins"""


@pytest.fixture(scope="session")
def network(pytestconfig: tp.Any) -> tp.Optional[str]:
    return PLATFORM_NETWORKS.get(
        pytestconfig.getoption("--network"), PLATFORM_NETWORKS["devnet"]
    )


@pytest.fixture(scope="session")
def neonpass_url(pytestconfig: tp.Any) -> tp.Optional[str]:
    return pytestconfig.environment.neonpass_url


@pytest.fixture(scope="session")
def solana_url(pytestconfig: tp.Any) -> tp.Optional[str]:
    return pytestconfig.environment.solana_url


@pytest.fixture(scope="session")
def chrome_extensions_path(required_extensions: tp.Union[tp.List, str]) -> pathlib.Path:
    """Extracting Chrome Plugins"""
    result_path = ""
    if isinstance(required_extensions, str):
        required_extensions = [required_extensions]
    for ext in required_extensions:
        source = (
            libs.extract_tar_gz(
                CHROME_TAR_PATH / f"{ext}.extension.tar.gz",
                CHROME_DATA_PATH / "plugins",
            )
            / ext
        )
        if not result_path:
            result_path = source
        else:
            result_path = result_path / f",{source}"
    yield result_path
    libs.rm_tree(CHROME_DATA_PATH)


@pytest.fixture(scope="function", autouse=True)
def chrome_extension_user_data() -> pathlib.Path:
    """Extracting Chrome extension user data"""
    user_data = (
        libs.extract_tar_gz(CHROME_TAR_PATH / "user_data.tar.gz", CHROME_DATA_PATH)
        / "user_data"
    )
    yield user_data
    libs.rm_tree(user_data)


@pytest.fixture(scope="session")
def chrome_extension_password() -> str:
    """Chrome extensions password `1234Neon5678`"""
    try:
        return os.environ["CHROME_EXT_PASSWORD"]
    except KeyError:
        raise AssertionError(
            "Please set the `CHROME_EXT_PASSWORD` environment variable (password for wallets)."
        )


@pytest.fixture
def use_persistent_context() -> bool:
    """Flag used for Chrome extensions load, set to False for standard pages not extensions"""
    return True


# @pytest.hookimpl(tryfirst=True, hookwrapper=True)
# def pytest_runtest_makereport(item, call):
#     """Save screenshot on fail"""
#     outcome = yield
#     rep = outcome.get_result()
#     if rep.when == 'call' and rep.failed:
#         mode = 'a' if os.path.exists('failures') else 'w'
#         try:
#             with open('failures', mode):
#                 if 'page' in item.fixturenames:
#                     page = item.funcargs['page']
#                 else:
#                     print('Fail to take screenshot')
#                     return
#             allure.attach(
#                 page.screenshot(full_page=True),
#                 name='screenshot',
#                 attachment_type=allure.attachment_type.PNG,
#                 extension="png"
#             )
#         except Exception as e:
#             print('Fail to take screenshot: {}'.format(e))


def pytest_exception_interact(node, call, report):
    """Attach allure screenshot"""
    context = False
    if hasattr(node, "funcargs") and node.funcargs['context']:
        context = node.funcargs['context']

    if report.failed and context and context.pages:
        for page in context.pages:
            if page.is_closed():
                continue
            allure.attach(
                page.screenshot(full_page=True),
                name="screenshot",
                attachment_type=allure.attachment_type.PNG,
                extension="png",
            )

# def save_screenshot_on_fail(request: pytest.FixtureRequest, page: Page):
#     if request.session.testsfailed and not page.is_closed():
#         allure.attach(
#             page.screenshot(full_page=True),
#             name="screenshot",
#             attachment_type=allure.attachment_type.PNG,
#             extension="png",
#         )


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
    config.addinivalue_line(
        "markers", "skip_browser(name): mark test to be skipped a specific browser"
    )
    config.addinivalue_line(
        "markers", "only_browser(name): mark test to run only on a specific browser"
    )


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

    skip_browsers_names = _get_skiplist(
        item, ["chrome", "chromium", "firefox", "webkit"], "browser"
    )

    if browser_name in skip_browsers_names:
        pytest.skip("skipped for this browser: {}".format(browser_name))
