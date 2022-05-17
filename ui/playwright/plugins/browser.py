import asyncio
import typing as tp
import urllib

import pytest
from _pytest.config import Config
from playwright.sync_api import Browser
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType
from playwright.sync_api import Page
from playwright.sync_api import Playwright
from playwright.sync_api import sync_playwright

from ui.libs import get_config


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


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    """Return a base URL"""
    base_url = pytestconfig.getoption("--base-url")
    if not base_url:
        raise AssertionError(f"Please setup --base-url")
    return base_url


@pytest.fixture(scope="session")
def browser_type_launch_args(pytestconfig: Config) -> tp.Dict:
    launch_options = {}
    headed_option = pytestconfig.getoption("--headed")
    if headed_option:
        launch_options["headless"] = False
    browser_channel_option = pytestconfig.getoption("--browser-channel")
    if browser_channel_option:
        launch_options["channel"] = browser_channel_option
    slowmo_option = pytestconfig.getoption("--slowmo")
    if slowmo_option:
        launch_options["slow_mo"] = slowmo_option

    return launch_options


@pytest.fixture(scope="session")
def browser_context_args() -> tp.Dict:
    return {"viewport": {"width": 1440, "height": 900}}


@pytest.fixture(scope="session")
def playwright() -> tp.Generator[Playwright, None, None]:
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="session")
def browser_type(playwright: Playwright, browser_name: str) -> BrowserType:
    if browser_name == "chrome":
        browser_name = "chromium"
    return getattr(playwright, browser_name)


@pytest.fixture(scope="session")
def launch_browser(
    playwright: Playwright,
    browser_type_launch_args: tp.Dict,
    browser_type: BrowserType,
    browser_name: str,
    pytestconfig: Config,
) -> tp.Callable[..., Browser]:
    def launch(**kwargs: tp.Dict) -> Browser:
        launch_options = {**browser_type_launch_args, **kwargs}
        browser = browser_type.launch(**launch_options)
        return browser

    def connect_to_remote(**kwargs: tp.Dict) -> Browser:
        connect_options = {"timeout": 60000}
        if "slow_mo" in kwargs:
            connect_options["slow_mo"] = kwargs["slow_mo"]
        args = {}
        url = f"ws://{pytestconfig.getoption('--remote-server')}:4444/playwright/{browser_name}/playwright-1.15.0?{urllib.parse.urlencode(args)}&headless=false"
        return browser_type.connect(ws_endpoint=url, **connect_options)

    if pytestconfig.getoption("--remote-server"):
        return connect_to_remote

    return launch


@pytest.fixture(scope="session")
def browser(launch_browser: tp.Callable[[], Browser]) -> tp.Generator[Browser, None, None]:
    browser = launch_browser()
    yield browser
    browser.close()


@pytest.fixture
def context(
    browser: Browser, browser_context_args: tp.Dict
) -> tp.Generator[BrowserContext, None, None]:
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


def _handle_page_goto(
    page: Page, args: tp.List[tp.Any], kwargs: tp.Dict[str, tp.Any], base_url: str
) -> None:
    url = args.pop()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = base_url + url
    return page._goto(url, *args, **kwargs)  # type: ignore


@pytest.fixture
def page(context: BrowserContext, base_url: str) -> tp.Generator[Page, None, None]:
    page = context.new_page()
    page._goto = page.goto  # type: ignore
    page.goto = lambda *args, **kwargs: _handle_page_goto(  # type: ignore
        page, list(args), kwargs, base_url
    )
    yield page
    page.close()


@pytest.fixture(scope="session")
def is_webkit(browser_name: str) -> bool:
    return browser_name == "webkit"


@pytest.fixture(scope="session")
def is_firefox(browser_name: str) -> bool:
    return browser_name == "firefox"


@pytest.fixture(scope="session")
def is_chromium(browser_name: str) -> bool:
    return browser_name == "chromium"


@pytest.fixture(scope="session")
def browser_name() -> None:
    return None


@pytest.fixture(scope="session")
def browser_channel(pytestconfig: tp.Any) -> tp.Optional[str]:
    return pytestconfig.getoption("--browser-channel")


def pytest_addoption(parser: tp.Any) -> None:
    group = parser.getgroup("uitests", "UI Tests")
    parser.addoption(
        "--base-url", metavar="url", default=None, help="base url for the application under test.",
    )

    parser.addoption(
        "--remote-server",
        action="store",
        default=None,
        help="Endpoint for remote selenium (moon) server",
    )

    group.addoption(
        "--browser", action="append", default=[], help="Browser engine which should be used",
    )
    group.addoption(
        "--headed", action="store_true", default=False, help="Run tests in headed mode.",
    )
    group.addoption(
        "--browser-channel", action="store", default=None, help="Browser channel to be used.",
    )
    group.addoption(
        "--slowmo", default=0, type="int", help="Run tests in slow mo",
    )
