import itertools
import logging
import pathlib
import shutil
import sys
import time
import uuid
from dataclasses import dataclass

import six

from ui.libs import exc

LOG = logging.getLogger(__name__)


@dataclass
class Tokens:
    neon: str = "NEON"
    usdt: str = "USDT"


BASE_USER_DATA_DIR = "user_data/tmp"
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
    #return shutil.copytree(extensions_dir / BASE_USER_DATA_DIR, extensions_dir / uuid.uuid4().hex)
    return extensions_dir / 'user_data'


def try_until(func, try_msg=None, error_msg=None, log=None, interval=1, timeout=360, times=None):
    """
    repeat call func while it returns False
    raises exc.TimeoutError if timeout expired or call times reached
    """
    log = log or LOG
    begin_msg = "Trying {0} until (timeout: {1} interval: {2} times: {3})".format(
        func, timeout, interval, times or "unlimited"
    )
    try_msg = try_msg or "{0} returns false".format(func)
    error_msg = error_msg or "Try {0} Failed!".format(try_msg)

    start_time = time.monotonic()
    log.debug(begin_msg)
    for num in itertools.count(1):
        log.debug("%s (%s) ...", try_msg, num)
        try:
            result = func()
            if result:
                return result
        except Exception as e:
            msg = "{0}: got error: {1}".format(error_msg, e)
            six.reraise(exc.Error, exc.Error(msg), sys.exc_info()[2])
        else:
            if time.monotonic() - start_time > timeout:
                msg = "{0}: timeout {1} seconds exceeded".format(error_msg, timeout)
                raise exc.TimeoutError(msg)
            if times and num >= times:
                msg = "{0}: call count {1} times exceeded".format(error_msg, times)
                raise exc.TimeoutError(msg)

        log.debug("Wait {:.2f} seconds before the next attempt".format(interval))
        time.sleep(interval)
