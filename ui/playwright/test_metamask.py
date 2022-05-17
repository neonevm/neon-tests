# coding: utf-8
"""
Created on 2021-10-01
@author: Eugeny Kurkovich
"""

import uuid

import pytest

from ui.pages import account_scope


class TestMetaMask:
    """Tests NeonEVM proxy functionality via MetaMask"""

    def test_launch(
        self, scalr_account_scope: account_scope.AccountDashboard,
    ):
        """Launch MetaMask ext and press button"""
        ws_name = uuid.uuid4().hex
        env_dashboard = scalr_account_scope.envs_menu.go_to_environment("tfenv1")
        workspaces_page = env_dashboard.open_workspaces()
        new_workspace_page = workspaces_page.open_new_workspace()
        new_workspace_page.set_workspace_name(ws_name)
        new_workspace_page.choose_vcs_provider("scalr-buildbot-te")
        new_workspace_page.choose_repository("Scalr/tf-revizor-fixtures")
        new_workspace_page.choose_configuration_version("local_wait")
        new_workspace_page.change_auto_apply_state()
        new_workspace_page.create_btn_click()
        workspaces_page = env_dashboard.open_workspaces()
        workspaces_page.refresh()
        assert (
            ws_name in workspaces_page.list_workspaces
        ), f"Workspace '{ws_name}' was not found in workspaces list"
        # Delete workspace
        ws_dashboard = workspaces_page.open_workspace_dashboard(ws_name)
        ws_settings_tab = ws_dashboard.open_settings_tab()
        ws_settings_tab.delete_workspace(ws_name)
        workspaces_page.page_loaded()
        workspaces_page.refresh()
        assert (
            ws_name not in workspaces_page.list_workspaces
        ), f"Workspace '{ws_name}' was not deleted"

