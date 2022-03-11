import functools
import json
import logging
import pathlib
import random
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
        "--network", type=str, env_var="NEON_NETWORK", default="night-stand", help="Test environment name."
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


class NeonProxyBaseTasksSet(TaskSet):
    """Implements base initialization, creates data requirements and helpers"""

    _accounts: tp.Optional[tp.List] = None
    """Cross user Accounts storage
    """
    _faucet: tp.Optional[Faucet] = None
    """Earn Free Cryptocurrencies service
    """

    _setup_class_locker = gevent.threading.Lock()
    _setup_class_done = False

    account: tp.Optional["eth_account.signers.local.LocalAccount"] = None
    web3_client: tp.Optional[NeonWeb3Client] = None

    @staticmethod
    def setup_class() -> None:
        """Base initialization"""
        NeonProxyBaseTasksSet.web3_client = NeonWeb3Client(credentials["proxy_url"], credentials["network_id"])
        NeonProxyBaseTasksSet._faucet = Faucet(credentials["faucet_url"])
        NeonProxyBaseTasksSet._accounts = []

    @staticmethod
    def extend_task(ext: str) -> tp.Callable:
        """Extends user task functional"""

        @functools.wraps(ext)
        def ext_runner(func: tp.Callable) -> tp.Callable:
            @functools.wraps(func)
            def task_wrapper(self, *args, **kwargs) -> tp.Any:
                getattr(self, ext)(*args, **kwargs)
                func(self, *args, **kwargs)

            return task_wrapper

        return ext_runner

    def get_block_number(self) -> None:
        """Check the number of the most recent block"""
        self.web3_client.get_block_number()

    def check_balance(self):
        """Keeps account balance not empty"""
        if self.web3_client.get_balance(self.account.address) < 10:
            # add credits to account
            self._faucet.request_neon(self.account.address)

    def setup(self) -> None:
        """Prepare data requirements"""
        # create new account for each simulating user
        self.account = self.web3_client.create_account()
        NeonProxyBaseTasksSet._accounts.append(self.account)

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        # setup class once
        with self._setup_class_locker:
            if not NeonProxyBaseTasksSet._setup_class_done:
                self.setup_class()
                NeonProxyBaseTasksSet._setup_class_done = True
        self.setup()


class NeonProxyTasksSet(NeonProxyBaseTasksSet):
    """Implements Neon proxy pipeline tasks"""

    @task
    @NeonProxyBaseTasksSet.extend_task("get_block_number")
    @NeonProxyBaseTasksSet.extend_task("check_balance")
    def send_neon(self) -> None:
        """Transferring funds to a random account"""
        # add credits to account
        recipient = random.choice(NeonProxyTasksSet._accounts)
        self.web3_client.send_neon(self.account, recipient, amount=10)


class NeonProxyUser(HttpUser):
    wait_time = between(1, 5)
    tasks = [NeonProxyTasksSet]
