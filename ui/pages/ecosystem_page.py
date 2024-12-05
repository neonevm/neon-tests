from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_class import BaseClass

class EcosystemPage(BaseClass):
    _url = "https://neonevm.org/ecosystem"

    join_our_ecosystem_button = (By.XPATH, "//span[@class='button__content'][contains(.,'Join Neon EVM Ecosystem')]")

    def assert_text_on_build_on_neon_block_link(self):
        EC.visibility_of_element_located(self.wait.until(EC.presence_of_element_located(EcosystemPage.join_our_ecosystem_button)))