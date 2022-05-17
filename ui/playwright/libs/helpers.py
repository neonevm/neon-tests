# coding: utf-8
"""
Created on 2021-10-05
@author: Eugeny Kurkovich
"""
import typing as tp

from tests.ui.libs import get_config
from tests.ui.libs import vcs as vcs_providers
from tests.ui.pages import github
from tests.ui.pages import vcs


def create_vcs_from_ui(
    oauth_app_name: str, vcs_name: str, vcs_page: vcs.VCSPage, logined_vcs: vcs_providers.VCSGitHub,
):
    """New VCS Providers creation from UI"""
    new_vcs_page = vcs_page.open_new_vcs()
    logined_vcs.create_oauth(oauth_app_name, new_vcs_page.callback_url)
    vcs_details = logined_vcs.get_app_settings(oauth_app_name)
    new_vcs_page.set_provider_name(vcs_name)
    new_vcs_page.set_client_id(vcs_details["key"])
    new_vcs_page.set_client_secret(vcs_details["secret"])
    new_vcs_page.create_button().click()
    if logined_vcs.name == "GitHub":
        page = github.GithubAuthPage(vcs_page.page)
    if not page.authorized:
        data = get_config("credentials.json")["github"]
        page.username.fill(data["username"])
        page.password.fill(data["password"])
        page.submit.click()
    page.authorize_user_button.click()
    vcs_page.page.wait_for_selector(f'text="{vcs_name}"')
