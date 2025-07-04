import itertools
import logging
import pathlib
import sys
import tarfile
import time
from dataclasses import dataclass
from enum import Enum

import six
from playwright.sync_api import BrowserContext, Page

from ui.libs import exc

LOG = logging.getLogger(__name__)


@dataclass
class Token:
    name: str
    address: str = None

    def __str__(self):
        return self.name


class TokenRegistry:
    """Holds all supported Tokens with their addresses."""

    NEON = Token("Neon", "89dre8rZjLNft7HoupGiyxu3MNftR577ZYu8bHe2kK7g")
    WNEON = Token("WNEON", "0x11adC2d986E334137b9ad0a0F290771F31e9517F")
    SOL = Token("SOL", "0xc7Fc9b46e479c5Cb42f6C458D1881e55E6B7986c")
    WSOL = Token("wSOL", "0xc7Fc9b46e479c5Cb42f6C458D1881e55E6B7986c")
    USDT = Token("USDT", "0x6eEf939FC6e2B3F440dCbB72Ea81Cd63B5a519A5")
    USDC = Token("USDC", "0x512E48836Cd42F3eB6f50CEd9ffD81E0a7F15103")
    BTC = Token("BTC", "0x5651a868392595baf4aa83639aecf232a4603cd9")


class Platform(Enum):
    """Enumeration of supported blockchain platforms."""

    SOLANA = "Solana"
    NEON = "Neon"


@dataclass
class TransactionFee:
    network_name: str
    token_name: str

    def __str__(self):
        return self.network_name


class TransactionFeeType(Enum):
    """Predefined transaction fee types for networks."""

    NEON = TransactionFee(Platform.NEON.value, TokenRegistry.NEON.name)
    SOL = TransactionFee(Platform.SOLANA.value, TokenRegistry.SOL.name)
    NONE = None


class PriorityFee(Enum):
    """Transaction priority fee levels."""

    FAST = "Fast"
    TURBO = "Turbo"
    ULTRA = "Ultra"
    CUSTOM = "Custom"
    NONE = None


BASE_USER_DATA_DIR = "user_data"
"""Base Path to a Chrome extensions User Data Directory."""

TMP_USER_DATA_DIR = f"/tmp/{BASE_USER_DATA_DIR}"
"""Temporary path to a MetaMask extension User Data Directory."""


def open_safe(context: BrowserContext, url: str, retry_count: int = 3) -> Page:
    while retry_count > 0:
        try:
            page = context.new_page()
            page.goto(url)
            return page
        except Exception as e:
            LOG.error(f"Failed to open page {url}: {e} retrying")
            retry_count -= 1
            if retry_count == 0:
                raise TimeoutError
            page.close()


def extract_tar_gz(source: pathlib.Path, dest: pathlib.Path) -> pathlib.Path:
    """Extract source into destination"""
    with tarfile.open(source) as file:
        file.extractall(dest)
    return dest


def rm_tree(p: pathlib.Path) -> None:
    """Remove directory recursively"""
    if p.is_file():
        p.unlink()
    else:
        for child in p.iterdir():
            rm_tree(child)
        p.rmdir()


def try_until(func, try_msg=None, error_msg=None, log=None, interval=1, timeout=360, times=None, raise_on_timeout=True):
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
                if not raise_on_timeout:
                    return
                else:
                    msg = "{0}: timeout {1} seconds exceeded".format(error_msg, timeout)
                    raise exc.TimeoutError(msg)
            if times and num >= times:
                if not raise_on_timeout:
                    return
                else:
                    msg = "{0}: call count {1} times exceeded".format(error_msg, times)
                    raise exc.TimeoutError(msg)
                raise exc.TimeoutError(msg)
        log.debug("Wait {:.2f} seconds before the next attempt".format(interval))
        time.sleep(interval)


# ... rest of the helpers (insert_cookies_to_context, rm_tree, clone_user_data, extract_tar_gz, try_until) unchanged ...
