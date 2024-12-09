import pytest
from selenium import webdriver
from ui.pages.developer_page import DeveloperPage
from ui.pages.ecosystem_page import EcosystemPage
from ui.pages.google_forms_page import GoogleFormsPage
from ui.pages.github_page import GithubPage
from ui.pages.main_page import MainPage
from ui.pages.menu import Menu
from ui.pages.quick_start_page import QuickStartPage
from utils.base_class import BaseClass

website_url = "https://neonevm.org/"

@pytest.fixture(scope="session", autouse=True)
def allure_environment():
    return None

@pytest.fixture(scope="function")
def driver(request):
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    driver.get(website_url)
    driver.maximize_window()
    yield driver
    driver.close()
    driver.quit()

@pytest.fixture(scope="function")
def main_page(driver):
    page = MainPage(driver, website_url)
    return page

@pytest.fixture(scope="function")
def menu_page(driver):
    page = Menu(driver, website_url)
    return page

@pytest.fixture(scope="function")
def developers_page(driver):
    page = DeveloperPage(driver, website_url)
    return page

@pytest.fixture(scope="function")
def ecosystem_page(driver):
    page = EcosystemPage(driver, website_url)
    return page

@pytest.fixture(scope="function")
def google_forms_page(driver):
    page = GoogleFormsPage(driver, website_url)
    return page

@pytest.fixture(scope="function")
def quick_start_page(driver):
    page = QuickStartPage(driver, None)
    return page

@pytest.fixture(scope="function")
def github_page(driver):
    page = GithubPage(driver, None)
    return page

@pytest.fixture(scope="function")
def base_class(driver):
    page = BaseClass(driver, website_url)
    return page