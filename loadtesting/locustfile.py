import json
import logging
import pathlib
import typing as tp

import gevent
from locust import HttpUser, TaskSet, between, events, task

from utils.faucet import Faucet
from utils.web3client import NeonWeb3Client

LOG = logging.getLogger("neon_client")

ENVS = "envs.json"
""" Default environment credentials storage 
"""


@events.init_command_line_parser.add_listener
def _(parser):
    """Add custom command line arguments to Locust"""
    parser.add_argument(
        "--network",
        type=str,
        env_var="NEON_NETWORK",
        default="night-stand",
        help="Test environment name."
    )
    parser.add_argument(
        "--credentials",
        type=str,
        env_var="NEON_CRED",
        default="",
        help="Absolute path to environment credentials file.",
    )


@events.test_start.add_listener
def _(environment, **kw):
    """Test start event handler"""
    cred = pathlib.Path(environment.parsed_options.credentials)
    network = environment.parsed_options.network
    if not (cred.exists() and cred.is_file()):
        cred = pathlib.Path(__file__).parent / ".." / ENVS
    with open(cred, "r") as fp:
        global credentials
        credentials = json.load(fp).get(network, dict())


class NeonProxyBaseTaskSet(TaskSet):

    _accounts: tp.Optional[tp.List] = None
    _faucet: tp.Optional[Faucet] = None
    _setup_class_locker = gevent.threading.Lock()
    _setup_class_done = False

    account: tp.Optional["eth_account.signers.local.LocalAccount"] = None
    web3_client: tp.Optional[NeonWeb3Client] = None

    @classmethod
    def setup_class(cls) -> None:
        cls.web3_client = NeonWeb3Client(credentials["proxy_url"], credentials["network_id"])
        cls._faucet = Faucet(credentials["faucet_url"])
        cls._accounts = []

    def setup(self) -> None:
        """Prepare data requirements"""
        self.account = self.web3_client.create_account()
        self._faucet.request_neon(self.account.address)
        NeonProxyBaseTaskSet._accounts.append(self.account)

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        # setup class once
        with self._setup_class_locker:
            if not NeonProxyBaseTaskSet._setup_class_done:
                self.setup_class()
                NeonProxyBaseTaskSet._setup_class_done = True
        self.setup()

    @task
    def _(self):
        print(f"{20*'-'}: Run task at {self}")


class Web3User(HttpUser):
    wait_time = between(1, 5)
    tasks = [NeonProxyBaseTaskSet]
