from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_class import BaseClass

class ExternalPages(BaseClass):

    quick_start_url = "https://neonevm.org/docs/quick_start"
    google_forms_url = "https://docs.google.com/forms/d/15iL4l-Rj3GUdtE1tlQTto2sqgMS5Gpn92u0GUveWWVg/viewform?edit_requested=true"
    github_url = "https://github.com/neonevm/neon-evm"
    check_google_forms_title = (By.XPATH, "//div[contains(text(),'Join our')]")

    def assert_text_on_googleform_title(self):
        assert "Join our Ecosystem" == self.wait.until(EC.presence_of_element_located(ExternalPages.check_google_forms_title)).text


