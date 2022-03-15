import functools
import json
import logging
import pathlib
import random
import typing as tp
import uuid

import gevent
import time
from locust import HttpUser, TaskSet, between, task, events

from utils.faucet import Faucet
from utils.web3client import NeonWeb3Client

LOG = logging.getLogger("neon_client")

ENV_FILE = "envs.json"
""" Default environment credentials storage 
"""


@events.init_command_line_parser.add_listener
def arg_parser(parser):
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
def load_credentials(environment, **kw):
    """Test start event handler"""
    cred = pathlib.Path(environment.parsed_options.credentials)
    network = environment.parsed_options.network
    if not (cred.exists() and cred.is_file()):
        cred = pathlib.Path(__file__).parent / ".." / ENV_FILE
    with open(cred, "r") as fp:
        global credentials
        credentials = json.load(fp).get(network, dict())


class LocustEventHandler(object):
    """Implements custom Locust events handler"""
    success = events.request_success
    failure = events.request_failure

    def __init__(self) -> None:
        self._buffer: tp.Dict[str, tp.Any] = dict()

    def init_event(
        self, task_id: str, request_type: str, task_name: tp.Optional[str] = "", start_time: tp.Optional[float] = None
    ) -> None:
        """Added data to buffer"""
        params = dict(
            name=task_name,
            start_time=start_time or time.time(),
            type=request_type,
        )
        self._buffer[task_id] = params
        LOG.debug("- buffer - %s" % self._buffer)

    def send_event(self, event_type: str, task_id: tp.Optional[str] = None, **kwargs) -> None:
        """Sends event to locust ."""
        event = self._buffer.pop(task_id, None)  # type: ignore
        end_time = time.time()
        if event:
            task_name = event["name"]
            total_time = round((end_time - event["start_time"]) * 1000, ndigits=3)
            event_params = dict(
                request_type=event["type"],
            )
        else:
            task_name = kwargs.get("name", str())
            total_time = round((end_time - kwargs.get("start_time", end_time - 1)) * 1000, ndigits=3)
            event_params = dict(
                request_type=kwargs.get("type", str()),
            )
        event_params["name"] = task_name
        event_params["response_length"] = float(kwargs.get("length", 0))
        event_params["response_time"] = total_time
        if event_type == "failure":
            event_params["exception"] = kwargs.get("exc_msg", None)
        # fire locust event
        getattr(self, event_type).fire(**event_params)
        LOG.debug("- %s : %s - %sms" % (event["type"], event_type, total_time))


locust_events_handler = LocustEventHandler()
"""Locust events handler
"""


def statistics_collector(func: tp.Callable) -> tp.Callable:
    """Handle locust events."""

    @functools.wraps(func)
    def wrap(self, *args, **kwargs) -> tp.Any:
        event: tp.Dict[str, tp.Any] = dict(
            task_id=str(uuid.uuid4()), request_type=f"`{func.__name__.replace('_', ' ')}`"
        )
        locust_events_handler.init_event(**event)
        response = None
        try:
            response = func(self, *args, **kwargs)
            event["event_type"] = "success"
        except Exception as err:
            event["exc_msg"] = err.args[0]
            event["event_type"] = "failure"
        locust_events_handler.send_event(**event)
        return response

    return wrap


class NeonWeb3ClientExt(NeonWeb3Client):
    """Extends Neon Web3 client adds statistics metrics"""

    @statistics_collector
    def send_neon(self, *args, **kwargs):
        super().send_neon(*args, **kwargs)


class NeonProxyBaseTasksSet(TaskSet):
    """Implements base initialization, creates data requirements and helpers"""

    _accounts: tp.Optional[tp.List] = None
    """Cross user Accounts storage
    """
    _faucet: tp.Optional[Faucet] = None
    """Earn Free Cryptocurrencies service
    """

    _neon_consumer_id: int = 0
    """Consumer id
    """

    _setup_class_locker = gevent.threading.Lock()
    _setup_class_done = False

    account: tp.Optional["eth_account.signers.local.LocalAccount"] = None
    neon_consumer_id: tp.Optional[int] = None
    web3_client: tp.Optional[NeonWeb3ClientExt] = None

    @staticmethod
    def setup_class() -> None:
        """Base initialization"""
        NeonProxyBaseTasksSet.web3_client = NeonWeb3Client(credentials["proxy_url"], credentials["network_id"])
        NeonProxyBaseTasksSet._faucet = Faucet(credentials["faucet_url"])
        NeonProxyBaseTasksSet._accounts = []

    def task_block_number(self) -> None:
        """Check the number of the most recent block"""
        self.web3_client.get_block_number()

    def task_keeps_balance(self):
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
            NeonProxyBaseTasksSet._neon_consumer_id += 1
            self.neon_consumer_id = NeonProxyBaseTasksSet._neon_consumer_id
        self.setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.neon_consumer_id)


def extend_task(*attrs) -> tp.Callable:
    """Extends user task functional"""

    @functools.wraps(*attrs)
    def ext_runner(func: tp.Callable) -> tp.Callable:
        @functools.wraps(func)
        def task_wrapper(self, *args, **kwargs) -> tp.Any:
            for attr in attrs:
                getattr(self, attr)(*args, **kwargs)
            func(self, *args, **kwargs)

        return task_wrapper

    return ext_runner


class NeonProxyTasksSet(NeonProxyBaseTasksSet):
    """Implements Neon proxy pipeline tasks"""

    @task
    @extend_task("task_block_number", "task_keeps_balance")
    @statistics_collector
    def send_neon(self) -> None:
        """Transferring funds to a random account"""
        # add credits to account
        recipient = random.choice(NeonProxyTasksSet._accounts)
        self.log.info(f"Send `neon` from {str(self.account.address)[:8]} to {str(recipient.address)[:8]}.")
        self.web3_client.send_neon(self.account, recipient, amount=10)


class NeonProxyUser(HttpUser):
    wait_time = between(1, 3)
    tasks = [NeonProxyTasksSet]
