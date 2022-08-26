# coding: utf-8
"""
Created on 2022-08-18
@author: Eugeny Kurkovich
"""
import functools
import json
import logging
import os
import pathlib
import random
import subprocess
import typing as tp
from dataclasses import dataclass

import requests
import web3
from solana.account import Account as SOLAccount
from solana.publickey import PublicKey
from solana.rpc import commitment
from solana.rpc.api import Client as solana_client

from ui.libs import try_until
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
DEFAULT_SOL_AMOUNT = 1000000 * 10 ** 9

CWD = pathlib.Path(__file__).parent
"""Current working directory"""

BASE_PATH = CWD.parent.parent
"""Project root directory"""


@dataclass
class SOLCommitmentState:
    """Bank states to solana query"""

    CONFIRMED: str = commitment.Confirmed
    FINALIZED: str = commitment.Finalized
    PROCESSED: str = commitment.Processed


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


def handle_failed_requests(func: tp.Callable) -> tp.Callable:
    """Extends solana client functional"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> tp.Any:
        resp = func(self, *args, **kwargs)
        if resp.get("error"):
            raise AssertionError(
                f"Request {func.__name__} is failed: {resp['error']['code']} - {resp['error']['message']}"
            )
        return resp["result"]

    return wrapper


class NeonClient:
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
            f"--commitment={SOLCommitmentState.PROCESSED} "
            f"--url {self._solana_url} "
            f"--evm_loader {self._loader_id} "
            f"{comand.replace('_','-')} {''.join(map(str, args))}"
        )
        try:
            return subprocess.check_output(cmd, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as err:
            print(f"ERR: neon-cli error {err}")
            raise


class OperatorAccount(SOLAccount):
    """Implements operator Account"""

    def __init__(self, key_id: tp.Optional[int] = None) -> None:
        self._path = CWD / f"operator-keypairs/id{key_id or ''}.json"
        if not self._path.exists():
            raise FileExistsError(f"Operator key `{self._path}` not exists")
        with open(self._path) as fd:
            key = json.load(fd)[:32]
        super(OperatorAccount, self).__init__(key)

    def get_path(self) -> str:
        """Return operator key storage path"""
        return self._path.as_posix()


class EvmLoader:
    """Implements base functionality of the evm loader"""

    def __init__(self, loader_id: str, solana_url: str, account: tp.Optional["OperatorAccount"] = None) -> None:
        self.loader_id = loader_id
        self.account = account
        self._neon_client = NeonClient(self.loader_id, solana_url)

    def ether2program(self, ether):
        """Create solana program from eth account, return program address and nonce"""

        if hasattr(ether, "address"):
            ether = ether.address
        elif not isinstance(ether, str):
            ether = ether.hex()
        if ether.startswith("0x"):
            ether = ether[2:]
        cli_output = self._neon_client.create_program_address(ether)
        items = cli_output.rstrip().split(" ")
        return items[0], int(items[1])


class SOLClient:
    """"""

    def __init__(self, credentials: tp.Dict = None, session: tp.Optional[tp.Any] = None) -> None:
        credentials = credentials or load_credentials()
        self._web3 = web3.Web3(web3.HTTPProvider(""))
        self._session = session or init_session(DEFAULT_USER_NUM)
        self._faucet = faucet.Faucet(credentials["faucet_url"], self._session)
        self._client = solana_client(credentials["solana_url"])
        self._evm_loader = EvmLoader(credentials["evm_loader"], credentials["solana_url"])

    def wait_confirmation(self, tx_sig: str, confirmations: tp.Optional[int] = 0) -> bool:
        """"""

        def get_signature_status():
            resp = self._client.get_signature_statuses([tx_sig])
            result = resp.get("result", {}).get("value")
            if result[0]:
                confirmation_status = result[0]["confirmationStatus"]
                confirmation_count = result[0]["confirmations"] or 0
                return (
                    confirmation_status == SOLCommitmentState.FINALIZED
                    or confirmation_status == SOLCommitmentState.CONFIRMED
                ) and confirmation_count >= confirmations
            return False

        return try_until(get_signature_status, interval=1, timeout=30)

    def create_eth_account(self) -> "eth_account.local.LocalAccount":
        account = self._web3.eth.account.create()
        self._faucet.request_neon(account.address, amount=DEFAULT_NEON_AMOUNT)
        return account

    def create_solana_program(self, account: "eth_account.local.LocalAccount") -> tp.Tuple[tp.Any]:
        return self._evm_loader.ether2program(account)

    @handle_failed_requests
    def get_sol_balance(
        self,
        address: tp.Union[str, "eth_account.signers.local.LocalAccount"],
        state: str = SOLCommitmentState.CONFIRMED,
    ) -> int:
        if isinstance(address, PublicKey):
            address = str(address)
        elif not isinstance(address, str):
            address = address.address
        return self._client.get_balance(address, commitment=state)

    @handle_failed_requests
    def request_airdrop(
        self,
        address: tp.Union[OperatorAccount, str],
        amount: int = DEFAULT_SOL_AMOUNT,
        state: str = SOLCommitmentState.CONFIRMED,
    ) -> tp.Any:
        """Requests sol to account"""
        if isinstance(address, OperatorAccount):
            address = address.public_key()
        elif isinstance(address, PublicKey):
            address = str(address)
        return self._client.request_airdrop(pubkey=address, lamports=amount, commitment=state)


sol_client = SOLClient()


def create_transaction():
    operator = OperatorAccount(random.choice(range(2, 31)))
    tx_sig = sol_client.request_airdrop(operator, 1000)
    sol_client.wait_confirmation(tx_sig)
    eth_account_address = sol_client.create_eth_account().address
    sol_account_address = sol_client.create_solana_program(eth_account_address)[0]
    sol_client.request_airdrop(sol_account_address, 1000)
    sol_client.wait_confirmation(tx_sig)
