from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from utils.base_page import BasePage


class BlogPage(BasePage):
    _url = "https://neonevm.org/blog"

    section_header = (By.XPATH, "//h1")
    author_icon = (By.XPATH, "//div[contains(@class,'120px')][1]//img")

    def assert_text_on_blog_page_title(self):
        element = self.wait.until(EC.presence_of_element_located(BlogPage.section_header))
        assert element.text == "Blog"

    def assert_post_not_empty(self):
        self.wait.until(EC.visibility_of_element_located(BlogPage.author_icon))
