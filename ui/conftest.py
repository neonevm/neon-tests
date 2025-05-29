import os
import pathlib
import typing as tp
import uuid
import pytest
import allure

from ui import libs
from ui.plugins import browser
from ui.pages import metamask
from ui.constants import PLATFORM_NETWORKS
from ui.tests.test_faucet import get_metamask_extension_id, BASE_NEON_BALANCE

from _pytest.config import Config
from playwright.sync_api import BrowserContext, BrowserType

CHROME_TAR_PATH = pathlib.Path(__file__).absolute().parent / "extensions" / "data"
CHROME_DATA_PATH = pathlib.Path(__file__).absolute().parent.parent / "chrome-data" / uuid.uuid4().hex
"""CHROME_DATA_PATH is temporary local destination in project to untar chrome data directory and plugins"""


@pytest.fixture(scope="session", autouse=True)
def allure_environment():
    """
    Override the allure_environment fixture to disable it
    """
    pass


@pytest.fixture(scope="session")
def network(pytestconfig: tp.Any) -> tp.Optional[str]:
    return PLATFORM_NETWORKS.get(pytestconfig.getoption("--network"), PLATFORM_NETWORKS["devnet"])


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
    user_data = libs.extract_tar_gz(CHROME_TAR_PATH / "user_data.tar.gz", CHROME_DATA_PATH) / "user_data"
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


@pytest.fixture(scope="session")
def required_extensions() -> tp.List:
    return "metamask"


@pytest.fixture
def context(
    browser_type: BrowserType,
    browser_context_args: tp.Dict,
    browser_type_launch_args: tp.Dict,
    chrome_extensions_path: pathlib.Path,
    chrome_extension_user_data: pathlib.Path,
    use_extension: bool,
) -> BrowserContext:
    """Override default context for MetaMasks load"""
    if use_extension:
        context = browser.create_persistent_context(
            browser_type,
            browser_context_args,
            browser_type_launch_args,
            ext_source=chrome_extensions_path,
            user_data_dir=chrome_extension_user_data.as_posix(),
        )
    else:
        context = browser_type.launch_persistent_context(
            user_data_dir="/tmp/without-extension",
            headless=False,
        )
    yield context
    context.close()


@pytest.fixture
def use_extension(request) -> bool:
    marker = request.node.get_closest_marker("no_extension")
    return marker is None


def pytest_exception_interact(node, call, report):
    """Attach allure screenshot"""
    context = False
    if hasattr(node, "funcargs") and type(node.funcargs) is dict and node.funcargs.get("context"):
        context = node.funcargs.get("context")

    if report.failed and context and context.pages:
        for page in context.pages:
            if page.is_closed():
                continue
            try:
                allure.attach(
                    page.screenshot(full_page=True),
                    name="screenshot",
                    attachment_type=allure.attachment_type.PNG,
                    extension="png",
                )
            except Exception as e:
                print("Fail to take screenshot: {}".format(e))


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


@pytest.fixture
def metamask_page(
    context: BrowserContext,
    network: str,
    chrome_extension_password: str,
) -> metamask.MetaMaskAccountsPage:
    page = context.new_page()
    page.goto("about:blank")
    extension_id = get_metamask_extension_id(context)
    page.goto(f"chrome-extension://{extension_id}/home.html")

    login_page = metamask.MetaMaskLoginPage(page)
    popup_news = login_page.login(password=chrome_extension_password)
    mm_page = popup_news.close()
    mm_page.check_funds_protection()
    mm_page.change_network(network)
    mm_page.switch_assets()
    # wait MetaMask initialization
    libs.try_until(
        lambda: int(mm_page.neon_balance) != BASE_NEON_BALANCE,
        times=5,
        interval=2,
        raise_on_timeout=False,
    )

    return mm_page
