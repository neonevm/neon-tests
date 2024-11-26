import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select

@pytest.mark.usefixtures("setup")
class BaseClass:
    def __init__(self, driver):
        self.driver = driver

    def verify_link_presence(self, text):
        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, text)))

    def no_errors_on_page(self):
        response = requests.get(self.driver.current_url)
        assert response.status_code == 200, print("Not Found.")

    def select_option_by_text(self, locator, text):
        sel = Select(locator)
        sel.select_by_visible_text(text)