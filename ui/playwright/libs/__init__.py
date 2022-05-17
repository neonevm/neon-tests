import json
import pathlib

import pytest


def get_config(filename: str):
    # Used for local run without devbox
    base_path = pathlib.Path("~/.scalr-labs/")
    with open((base_path / filename).expanduser(), "r") as rev_conf:
        return json.load(rev_conf)


def insert_cookies_to_context(resp_cookies, context):
    cookies = []
    for cook in resp_cookies:
        if cook.name.startswith("__"):  # playwright can't load this cookies, don't know why
            continue
        cookies.append(
            {"name": cook.name, "value": cook.value, "domain": cook.domain, "path": cook.path,}
        )
    context.add_cookies(cookies)
