from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_page import BasePage


class GoogleFormsPage(BasePage):
    _url = "https://docs.google.com/forms/d/15iL4l-Rj3GUdtE1tlQTto2sqgMS5Gpn92u0GUveWWVg/viewform?edit_requested=true"

    check_google_forms_title = (By.XPATH, "(//form//*[@role='heading'])[1]")

    def assert_text_on_googleform_title(self):
        element = self.wait.until(EC.presence_of_element_located(GoogleFormsPage.check_google_forms_title))
        assert element.text == "Join our Ecosystem"
