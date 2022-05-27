import pathlib
import shutil
import uuid


from dataclasses import dataclass


@dataclass
class Tokens:
    neon: str = "NEON"
    usdt: str = "USDT"


BASE_USER_DATA_DIR = "user_data"
"""Path to a Chrome extensions User Data Directory, which stores browser session data like cookies and local storage.
"""


def insert_cookies_to_context(resp_cookies, context):
    cookies = []
    for cook in resp_cookies:
        if cook.name.startswith("__"):  # playwright can't load this cookies, don't know why
            continue
        cookies.append(
            {
                "name": cook.name,
                "value": cook.value,
                "domain": cook.domain,
                "path": cook.path,
            }
        )
    context.add_cookies(cookies)


def rm_tree(p: pathlib.Path) -> None:
    """Remove directory recursively"""
    if p.is_file():
        p.unlink()
    else:
        for child in p.iterdir():
            rm_tree(child)
        p.rmdir()


def clone_user_data(extensions_dir: pathlib.Path) -> pathlib.Path:
    """Clone chrome extension user data"""
    return shutil.copytree(extensions_dir / BASE_USER_DATA_DIR, extensions_dir / uuid.uuid4().hex)
