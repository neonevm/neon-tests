import functools
import json
import logging
import pathlib
import random
import sys
import time
import typing as tp
import uuid

import gevent
import requests
from locust import User, TaskSet, between, task, events, tag

from utils import helpers
from utils.faucet import Faucet
from utils.web3client import NeonWeb3Client

LOG = logging.getLogger("neon_client")

DEFAULT_NETWORK = "night-stand"
"""Default test environment name
"""

ENV_FILE = "envs.json"
""" Default environment credentials storage 
"""

ERC20_VERSION = "0.6.6"
"""ERC20 Protocol version
"""

INCREASE_STORAGE_VERSION = "0.8.10"
"""Increase Storage Protocol version
"""


def init_session(size: int) -> requests.Session:
    """init request session with extended connection pool size"""
    adapter = requests.adapters.HTTPAdapter(pool_connections=size, pool_maxsize=size, pool_block=True)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


@events.init_command_line_parser.add_listener
def arg_parser(parser):
    """Add custom command line arguments to Locust"""
    parser.add_argument(
        "--credentials",
        type=str,
        env_var="NEON_CRED",
        default=ENV_FILE,
        help="Relative path to environment credentials file.",
    )


@events.test_start.add_listener
def load_credentials(environment, **kwargs):
    """Test start event handler"""
    base_path = pathlib.Path(__file__).parent.parent
    path = base_path / environment.parsed_options.credentials
    network = environment.parsed_options.host
    if not (path.exists() and path.is_file()):
        path = base_path / ENV_FILE
    with open(path, "r") as fp:
        global credentials
        f = json.load(fp)
        credentials = f.get(network, f[DEFAULT_NETWORK])


class LocustEventHandler(object):
    """Implements custom Locust events handler"""

    def __init__(self, request_event: "EventHook") -> None:
        self.buffer: tp.Dict[str, tp.Any] = dict()
        self._request_event = request_event

    def init_event(
        self, task_id: str, request_type: str, task_name: tp.Optional[str] = "", start_time: tp.Optional[float] = None
    ) -> None:
        """Added data to buffer"""
        params = dict(
            name=task_name,
            start_time=start_time or time.time(),
            request_type=request_type,
            start_perf_counter=time.perf_counter(),
        )
        self.buffer[task_id] = params
        LOG.debug("- buffer - %s" % self.buffer)

    def fire_event(self, task_id: str, **kwargs) -> None:
        """Sends event to locust ."""
        event = self.buffer.pop(task_id)
        total_time = (time.perf_counter() - event["start_perf_counter"]) * 1000
        request_meta = dict(
            name=event["name"],
            request_type=event["request_type"],
            response=event.get("response"),
            response_time=total_time,
            response_length=event.get("response_length", 0),
            exception=event.get("exception"),
            context={},
        )
        self._request_event.fire(**request_meta)
        LOG.debug("- %s : %s - %sms" % (event["request_type"], event["event_type"], total_time))


locust_events_handler = LocustEventHandler(events.request)


def statistics_collector(func: tp.Callable) -> tp.Callable:
    """Handle locust events."""

    @functools.wraps(func)
    def wrap(*args, **kwargs) -> tp.Any:
        task_id = str(uuid.uuid4())
        request_type = f"`{func.__name__.replace('_', ' ')}`"
        event: tp.Dict[str, tp.Any] = dict(task_id=task_id, request_type=request_type)
        locust_events_handler.init_event(**event)
        response = None
        try:
            response = func(*args, **kwargs)
            event = dict(response=response, response_length=sys.getsizeof(response), event_type="success")
        except Exception as err:
            event = dict(event_type="failure", exception=err)
            LOG.error(f"web3 RPC call {request_type} is failed: {err}")
        locust_events_handler.buffer[task_id].update(event)
        locust_events_handler.fire_event(task_id)
        return response

    return wrap


class NeonWeb3ClientExt(NeonWeb3Client):
    """Extends Neon Web3 client adds statistics metrics"""

    def __getattribute__(self, item):
        ignore_list = ["create_account"]
        attr = super(NeonWeb3ClientExt, self).__getattribute__(item)
        if callable(attr) and item not in ignore_list:
            attr = statistics_collector(attr)
        return attr


class NeonProxyTasksSet(TaskSet):
    """Implements base initialization, creates data requirements and helpers"""

    _accounts: tp.Optional[tp.List] = None
    """Cross user Accounts storage
    """
    _erc20_contracts: tp.Optional[tp.Dict] = None
    """user erc20 contracts storage 
    """

    _increase_storage_contracts: tp.Optional[tp.Dict] = None
    """user `IncreaseStorage` contracts storage 
    """

    _faucet: tp.Optional[Faucet] = None
    """Earn Free Cryptocurrencies service
    """

    _last_consumer_id: int = 0
    """Last spawned user id
    """

    _setup_class_locker = gevent.threading.Lock()
    _setup_class_done = False

    account: tp.Optional["eth_account.signers.local.LocalAccount"] = None
    neon_consumer_id: tp.Optional[int] = None
    """Spawned user id
    """
    web3_client: tp.Optional[NeonWeb3ClientExt] = None

    @staticmethod
    def setup_class() -> None:
        """Base initialization"""
        NeonProxyTasksSet._accounts = []
        NeonProxyTasksSet._erc20_contracts = {}

    def setup(self) -> None:
        """Prepare data requirements"""
        # create new account for each simulating user
        self.account = self.web3_client.create_account()
        self._increase_storage_contracts = []
        NeonProxyTasksSet._accounts.append(self.account)

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        # setup class once
        with self._setup_class_locker:
            if not NeonProxyTasksSet._setup_class_done:
                self.setup_class()
                NeonProxyTasksSet._setup_class_done = True
            NeonProxyTasksSet._last_consumer_id += 1
            self.neon_consumer_id = NeonProxyTasksSet._last_consumer_id
            session = init_session(
                self.user.environment.parsed_options.num_users or self.user.environment.runner.target_user_count
            )
            self._faucet = Faucet(credentials["faucet_url"], session=session)
            self.web3_client = NeonWeb3ClientExt(credentials["proxy_url"], credentials["network_id"], session=session)
        self.setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.neon_consumer_id)

    def task_block_number(self) -> None:
        """Check the number of the most recent block"""
        self.web3_client.get_block_number()

    def task_keeps_balance(self) -> None:
        """Keeps account balance not empty"""
        if self.web3_client.get_balance(self.account.address) < 100:
            # add credits to account
            self._faucet.request_neon(self.account.address)

    def deploy_contract(
        self,
        name: str,
        version: str,
        account: "eth_account.signers.local.LocalAccount",
        constructor_args: tp.Optional[tp.Any] = None,
        gas: tp.Optional[int] = 0,
    ) -> "web3._utils.datatypes.Contract":
        """contract deployments"""

        contract_interface = helpers.get_contract_interface(name, version)

        contract_deploy_tx = self.web3_client.deploy_contract(
            account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            constructor_args=constructor_args,
            gas=gas,
        )

        if not (contract_deploy_tx and contract_interface):
            return None, None

        contract = self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

        return contract, contract_deploy_tx


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


@tag("send_neon")
class NeonTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    @task
    @extend_task("task_block_number", "task_keeps_balance")
    def task_send_neon(self) -> None:
        """Transferring funds to a random account"""
        # add credits to account
        recipient = random.choice(self._accounts)
        self.log.info(f"Send `neon` from {str(self.account.address)[:8]} to {str(recipient.address)[:8]}.")
        self.web3_client.send_neon(self.account, recipient, amount=1)


@tag("erc20")
class ERC20TasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    _erc20_version = ERC20_VERSION

    @task(1)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy ERC20 contract"""
        self.log.info(f"Deploy `ERC20` contract.")
        contract, _ = self.deploy_contract("ERC20", self._erc20_version, self.account, constructor_args=[pow(10, 10)])
        if not contract:
            self.log.info("ERC20 contract deployment failed")
            return
        self._erc20_contracts.setdefault(self.account.address, set()).add(contract)

    @task(5)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_send_erc20(self) -> None:
        """Send ERC20 tokens"""
        contracts = self._erc20_contracts.get(self.account.address)
        if contracts:
            contract = random.choice(tuple(contracts))
            recipient = random.choice(self._accounts)
            self.log.info(f"Send `erc20` tokens from {str(contract.address)[:8]} to {str(recipient.address)[:8]}.")
            if self.web3_client.send_erc20(self.account, recipient, 1, contract.address, abi=contract.abi):
                self._erc20_contracts.setdefault(recipient.address, set()).add(contract)
            # remove contracts without balance
            if contract.functions.balanceOf(self.account.address).call() < 1:
                self.log.info(f"Remove contract `{contract.address[:8]}` with empty balance")
                contracts.remove(contract)
            return
        self.log.info("no `ERC20` contracts found, send is cancel")


@tag("increase_storage")
class IncreaseStorageTasksSet(NeonProxyTasksSet):
    """Implements IncreaseStorage base pipeline tasks"""

    _inc_storage_version = INCREASE_STORAGE_VERSION

    @task(1)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy IncreaseStorage contract"""
        self.log.info(f"Deploy `IncreaseStorage` contract.")
        contract, _ = self.deploy_contract("IncreaseStorage", self._inc_storage_version, self.account)
        if not contract:
            self.log.info("`IncreaseStorage` contract deployment failed")
            return
        self._increase_storage_contracts.append(contract)

    @task(5)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_account_resize(self) -> None:
        """Accounts resize"""
        contracts = self._increase_storage_contracts
        if contracts:
            contract = random.choice(contracts)
            self.log.info(f"Increase account {str(contract.address)[:8]}.")
            inc_tx = contract.functions.inc().buildTransaction(
                {
                    "from": self.account.address,
                    "nonce": self.web3_client.eth.get_transaction_count(self.account.address),
                    "gasPrice": self.web3_client.gas_price(),
                }
            )
            self.web3_client.send_transaction(self.account, inc_tx)
            return
        self.log.info("no `IncreaseStorage` contracts found, account resize canceled")


class NeonPipelineUser(User):
    """class represents a base Neon pipeline by one user"""

    wait_time = between(1, 3)

    tasks = {ERC20TasksSet: 1, IncreaseStorageTasksSet: 1, NeonTasksSet: 3}
