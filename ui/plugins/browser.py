import typing as tp
import urllib
import pathlib

import httpagentparser
import pytest
from _pytest.config import Config
from playwright.sync_api import Browser
from playwright.sync_api import BrowserContext
from playwright.sync_api import BrowserType
from playwright.sync_api import Page
from playwright.sync_api import Playwright
from playwright.sync_api import sync_playwright

from clickfile import create_allure_environment_opts


def create_persistent_context(
    browser_type: BrowserType,
    browser_context_args: tp.Dict,
    browser_type_launch_args: tp.Dict,
    ext_source: tp.Union[str, pathlib.Path],
    user_data_dir: tp.Union[str, pathlib.Path],
) -> BrowserContext:
    """Creates persistent context useed for Chrome extensions load"""
    if isinstance(ext_source, str):
        ext_source = pathlib.Path(ext_source)
    if isinstance(user_data_dir, str):
        user_data_dir = pathlib.Path(user_data_dir)
    launch_options = {
        "args": [
            f"--disable-extensions-except={ext_source}",
            f"--load-extension={ext_source}",
        ],
        "headless": False,
        "user_data_dir": user_data_dir,
        **browser_type_launch_args,
        **browser_context_args,
    }
    return browser_type.launch_persistent_context(**launch_options)


@pytest.fixture(scope="session")
def base_url(pytestconfig):
    """Return a base URL"""
    base_url = pytestconfig.getoption("--basic-url")
    if not base_url:
        pass
        # raise AssertionError(f"Please setup --basic-url")
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
def browser(launch_browser: tp.Callable[[], Browser], pytestconfig: Config) -> tp.Generator[Browser, None, None]:
    browser = launch_browser()
    yield browser
    browser.close()


@pytest.fixture
def context(
    browser: Browser,
    browser_context_args: tp.Dict,
) -> tp.Generator[BrowserContext, None, None]:
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


def _handle_page_goto(page: Page, args: tp.List[tp.Any], kwargs: tp.Dict[str, tp.Any], base_url: str) -> None:
    url = args.pop()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = base_url + url
    return page._goto(url, *args, **kwargs)  # type: ignore


@pytest.fixture
def page(context: BrowserContext, base_url: str, use_persistent_context: bool) -> tp.Generator[Page, None, None]:
    if use_persistent_context:
        page = context.wait_for_event("page", timeout=60000)
    else:
        page = context.new_page()
    page._goto = page.goto  # type: ignore
    page.goto = lambda *args, **kwargs: _handle_page_goto(page, list(args), kwargs, base_url)  # type: ignore

    user_agent = page.evaluate("navigator.userAgent")
    agent_data = httpagentparser.detect(user_agent)
    opts = {
        "Browser": agent_data['browser']['name'],
        "Browser.Version": agent_data['browser']['version'],
    }
    create_allure_environment_opts(opts)

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
        "--basic-url",
        # metavar="url",
        default="",
        help="base url for the application under test.",
    )

    # parser.addoption(
    #     "--remote-server",
    #     action="store",
    #     default=None,
    #     help="Endpoint for remote selenium (moon) server",
    # )
    #
    # group.addoption(
    #     "--browser",
    #     action="append",
    #     default=[],
    #     help="Browser engine which should be used",
    # )
    # group.addoption(
    #     "--headed",
    #     action="store_true",
    #     default=False,
    #     help="Run tests in headed mode.",
    # )
    # group.addoption(
    #     "--browser-channel",
    #     action="store",
    #     default=None,
    #     help="Browser channel to be used.",
    # )
    # group.addoption(
    #     "--slowmo",
    #     default=0,
    #     type=int,
    #     help="Run tests in slow mo",
    # )
    # group.addoption(
    #     "--screenshot",
    #     default="off",
    #     choices=["on", "off", "only-on-failure"],
    #     help="Whether to automatically capture a screenshot after each test.",
    # )
