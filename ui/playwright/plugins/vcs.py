import logging
import time
import typing as tp

import _pytest.fixtures
import pytest

from tests.ui.libs import get_config
from tests.ui.libs import helpers
from tests.ui.libs import vcs as vcs_providers
from tests.ui.pages import account_scope

LOG = logging.getLogger(__name__)


def pytest_generate_tests(metafunc) -> None:
    """
    Add params to fixture loggined_vcs from mark pytest.mark.vcs('github', 'gitlab')
    """
    marks = ""
    if hasattr(metafunc.function, "pytestmark"):
        marks = metafunc.function.pytestmark
    if hasattr(metafunc.cls, "pytestmark"):
        marks = metafunc.cls.pytestmark
    for mark in marks:
        if mark.name == "vcs":
            metafunc.parametrize(
                **{"argnames": "logined_vcs", "argvalues": mark.args, "ids": []}, indirect=True
            )
            break


@pytest.fixture(scope="session")
def logined_vcs(request: _pytest.fixtures.SubRequest,) -> vcs_providers.VCSGitHub:
    """Return logined VCS (github, gitlab, etc)"""
    vcs_type = request.param or "github"
    credentials = get_config("credentials.json")

    if vcs_type not in credentials:
        raise AssertionError(f"Credentials for {vcs_type} not found if credentials.json")

    vcs_credentials = credentials[vcs_type]

    provider = vcs_providers.Providers[vcs_type].value()

    if pytest.is_drone:
        proxy = credentials.get("tests_proxy")
        provider._session.proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}",
        }

    LOG.debug(
        f'Authorize vcs {provider.name} with {vcs_credentials["username"]}:{vcs_credentials["password"]}'
    )
    resp = provider.login(vcs_credentials["username"], vcs_credentials["password"])
    if resp.status_code not in [200, 201, 302]:
        raise AssertionError(f"Can't authorize VCS {resp.status_code}")
    elif "Sign in to GitHub" in resp.text:
        raise AssertionError(f"Can't authorize VCS, invalid user name or password")

    return provider


@pytest.fixture
def create_vcs(
    logined_vcs: vcs_providers.VCSGitHub,
    scalr_account_scope: account_scope.AccountDashboard,
    test_id: str,
) -> str:
    """New VCS Providers creation from UI fixture"""
    app_name = f"test-{test_id}"
    vcs_page = scalr_account_scope.open_vcs()
    time.sleep(1)
    helpers.create_vcs_from_ui(app_name, app_name, vcs_page, logined_vcs)
    yield app_name
    try:
        logined_vcs.delete_oauth(app_name)
    except:
        pass
