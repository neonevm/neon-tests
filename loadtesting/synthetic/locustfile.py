# coding: utf-8
"""
Created on 2022-08-18
@author: Eugeny Kurkovich
"""

import json
import logging
import os
import pathlib
import subprocess
import typing as tp

import requests
import web3
from solana.account import Account as SOLAccount
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

CWD = pathlib.Path(__file__).parent
"""Current working directory"""

BASE_PATH = CWD.parent.parent
"""Project root directory"""


def init_session(size: int) -> requests.Session:
    """init request session with extended connection pool size"""
    adapter = requests.adapters.HTTPAdapter(pool_connections=size, pool_maxsize=size, pool_block=True)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def load_credentials(*args, **kwargs) -> tp.Dict:
    """Test start event handler"""
    path = BASE_PATH / ENV_FILE
    with open(path, "r") as fp:
        f = json.load(fp)
        return f[DEFAULT_NETWORK]


class NeonCli:
    """Implements neon client functionality"""

    def __init__(self, evm_loader_id: str, solana_url: str, verbose_flags: tp.Optional[str] = "") -> None:
        self._verbose_flags = verbose_flags
        self._loader_id = evm_loader_id
        self._solana_url = solana_url

    def __getattr__(self, item):

        global command
        command = item

        def wrapper(*args, **kwargs):
            return self._run_cli(command, *args, **kwargs)

        return wrapper

    def _run_cli(self, comand, *args):
        cmd = (
            f"neon-cli {self._verbose_flags} "
            f"-vvv "
            f"--commitment=processed "
            f"--url {self._solana_url} "
            f"--evm_loader {self._loader_id} "
            f"{comand.replace('_','-')} {''.join(map(str, args))}"
        )
        try:
            return subprocess.check_output(cmd, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as err:
            print(f"ERR: neon-cli error {err}")
            raise


class OperatorAccount:
    """Implements operator Account"""

    def __init__(self, path=None) -> None:
        self._path = path or CWD / "operator-keypairs/id.json"
        self.account = self._create_account()

    def _create_account(self) -> "solana.account.Account":
        """Create an operator Account"""
        with open(self.path) as fd:
            key = json.load(fd)
            return SOLAccount(key[0:32])

    def get_path(self) -> str:
        """Return operator key storage path"""
        return self._path.as_posix()


class EvmLoader:
    """Implements base functionality of the evm loader"""

    def __init__(self, loader_id: str, solana_url: str, account: tp.Optional["OperatorAccount"] = None) -> None:
        self.loader_id = loader_id
        self.account = account
        self._neon_cli = NeonCli(self.loader_id, solana_url)

    def ether2program(self, ether):
        """Create solana program from eth account"""

        if hasattr(ether, "address"):
            ether = ether.address
        elif not isinstance(ether, str):
            ether = ether.hex()
        if ether.startswith("0x"):
            ether = ether[2:]
        cli_output = self._neon_cli.create_program_address(ether)
        items = cli_output.rstrip().split(' ')
        return items[0], int(items[1])


class SOLClient:
    def __init__(self, credentials: tp.Dict = None, session: tp.Optional[tp.Any] = None) -> None:
        credentials = credentials or load_credentials()
        self._web3 = web3.Web3(web3.HTTPProvider(""))
        self._session = session or init_session(DEFAULT_USER_NUM)
        self._faucet = faucet.Faucet(credentials["faucet_url"], self._session)
        self._solana = solana_api_client(credentials["solana_url"])
        self._evm_loader = EvmLoader(credentials["evm_loader"], credentials["solana_url"])

    def create_eth_account(self) -> "eth_account.local.LocalAccount":
        account = self._web3.eth.account.create()
        self._faucet.request_neon(account.address, amount=DEFAULT_NEON_AMOUNT)
        return account

    def create_solana_program(self, account: "eth_account.local.LocalAccount") -> tp.Tuple[tp.Any]:
        return self._evm_loader.ether2program(account)

    def get_sol_balance(self, address: tp.Union[str, "eth_account.signers.local.LocalAccount"]) -> int:
        if not isinstance(address, str):
            address = address.address
        return self._solana.get_balance(address)
