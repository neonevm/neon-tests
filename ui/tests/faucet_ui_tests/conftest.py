import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from ui.pages.faucet_page import FaucetPage
from utils.base_page import BasePage

website_url = "https://neonfaucet.org/"


@pytest.fixture(scope="function")
def driver(request: pytest.FixtureRequest):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.implicitly_wait(10)
    driver.get(website_url)
    driver.maximize_window()
    yield driver
    driver.close()
    driver.quit()


@pytest.fixture(scope="function")
def faucet_page(driver):
    page = FaucetPage(driver, website_url)
    return page


@pytest.fixture(scope="function")
def base_page(driver):
    page = BasePage(driver, website_url)
    return page
