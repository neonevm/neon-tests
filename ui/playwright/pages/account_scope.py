import time
from typing import Literal

from ui.pages import account_users
from ui.pages import vcs as vcs_page

from . import BasePage


class AccountDashboard(BasePage):
    def __init__(self, *args, **kwargs):
        super(AccountDashboard, self).__init__(*args, **kwargs)

    def page_loaded(self):
        self.page.wait_for_selector("text='Account Dashboard'", state="visible", timeout=120000)


    def open_vcs(self) -> vcs_page.VCSPage:
        if not self.page.query_selector("//span[text()='New VCS Provider']/ancestor::a"):
            for item in self.menu.get_items():
                if item.text_content() == "VCS providers":
                    self.menu.open()
                    item.click()
                    break
        return vcs_page.VCSPage(self.page)

    def open_iam_submenu(
        self,
        submenu_key: Literal[
            "Users", "Service accounts", "Teams", "Roles", "SSO", "Access policies"
        ],
    ):

        pages = {"Users": account_users.AccountUsers}

        for menu_item in self.menu.get_items():
            if menu_item.text_content() == "IAM":
                self.menu.open()
                menu_item.hover()
                time.sleep(0.7)
                submenu_focus_item = self.page.query_selector_all("div.x-menu-item-active")[1]
                submenu = submenu_focus_item.query_selector("//../..")
                subitems = submenu.query_selector_all(".x-box-item:not(.x-menu-item-separator)")
                for subitem in subitems:
                    if subitem.text_content() == submenu_key:
                        subitem.hover(timeout=500)
                        time.sleep(0.7)
                        subitem.click(timeout=1000)
                        self.page.is_visible('text="Loading page..."')
                        self.page.wait_for_selector('text="Loading page..."', state="hidden")
                        return pages[submenu_key](self.page)
