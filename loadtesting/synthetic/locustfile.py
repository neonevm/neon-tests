# coding: utf-8
"""
Created on 2022-08-18
@author: Eugeny Kurkovich
"""

import json
import logging
import os
import pathlib
import typing as tp

import requests
import web3
from solana.rpc.api import Client as solana_api_client

from utils import faucet

LOG = logging.getLogger("sol-client")

DEFAULT_NETWORK = os.environ.get("NETWORK", "night-stand")
"""Default test environment name
"""

ENV_FILE = "envs.json"
""" Default environment credentials storage 
"""

DEFAULT_USER_NUM = 10
"""
"""

DEFAULT_NEON_AMOUNT = 100
"""
"""


def init_session(size: int) -> requests.Session:
    """init request session with extended connection pool size"""
    adapter = requests.adapters.HTTPAdapter(pool_connections=size, pool_maxsize=size, pool_block=True)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def load_credentials(*args, **kwargs) -> tp.Dict:
    """Test start event handler"""
    base_path = pathlib.Path(__file__).parent.parent.parent
    path = base_path / ENV_FILE
    with open(path, "r") as fp:
        f = json.load(fp)
        return f[DEFAULT_NETWORK]


class SOLClient:
    def __init__(self, credentials: tp.Dict = None, session: tp.Optional[tp.Any] = None) -> None:
        credentials = credentials or load_credentials()
        self._web3 = web3.Web3(web3.HTTPProvider(""))
        self._session = session or init_session(DEFAULT_USER_NUM)
        self._faucet = faucet.Faucet(credentials["faucet_url"], self._session)
        self._solana = solana_api_client(credentials["solana_url"])

    def create_account(self) -> "eth_account.local.LocalAccount":
        account = self._web3.eth.account.create()
        self._faucet.request_neon(account.address, amount=DEFAULT_NEON_AMOUNT)
        return account

    def get_sol_balance(self, address: tp.Union[str, "eth_account.signers.local.LocalAccount"]) -> int:
        if not isinstance(address, str):
            address = address.address
        return self._solana.get_balance(address)
