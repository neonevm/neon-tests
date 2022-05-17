import logging

import requests

LOG = logging.getLogger(__name__)


def authorize_scalr(url: str, login: str, password: str) -> requests.Response:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/80.0.3071.115 Safari/537.36 Revizor",
            "X-Scalr-Csrf": "null",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
    )
    init_params = session.get(f"{url}/guest/xInit").json()
    providers = init_params["initParams"]["context"]["identityProviders"]
    provider = [p for p in providers if providers[p]["type"] == "scalr"][0]
    resp = session.post(
        f"{url}/guest/xLogin",
        {"scalrLogin": login, "scalrPass": password, "identityProviderId": provider},
    )

    body = resp.json()

    if not body["success"]:
        raise AssertionError(f"Can't authorize on scalr {url} with {login}:{password} ({body})")
    return resp
