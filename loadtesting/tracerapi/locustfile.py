# coding: utf-8
"""
Created on 2022-08-31
@author: Eugeny Kurkovich
"""
import functools
import json
import logging
import os
import pathlib
import random
import sys
import time
import typing as tp
import uuid

import gevent
import requests
import web3
from locust import User, TaskSet, between, task, events, tag

from utils import apiclient

LOG = logging.getLogger("neon_client")

DEFAULT_NETWORK = "night-stand"
"""Default test environment name
"""

ENV_FILE = "envs.json"
""" Default environment credentials storage 
"""

DUMPED_DATA = "dumped_data/transaction.json"
"""Path to transaction history
"""

NEON_RPC = os.environ.get("NEON_RPC")
"""Endpoint to Neon-RPC. Neon-RPC is a single RPC entrypoint to Neon-EVM. 
The function of this service is so route requests between Tracer API and Neon Proxy services
"""


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
    parser.add_argument(
        "--neon_rpc",
        type=str,
        env_var="NEON_RPC",
        default=None,
        help="Relative path to environment credentials file.",
    )


@events.test_start.add_listener
def load_requirements(environment, **kwargs):
    """Test start event handler"""
    # load test env credentials
    root_path = list(pathlib.Path(__file__).parents)[2]
    path_to_credentials = root_path / environment.parsed_options.credentials
    network = environment.parsed_options.host
    if not (path_to_credentials.exists() and path_to_credentials.is_file()):
        path_to_credentials = root_path / ENV_FILE
    with open(path_to_credentials, "r") as fp:
        global credentials
        f = json.load(fp)
        credentials = f.get(network, f[DEFAULT_NETWORK])
    # load transaction history
    path = pathlib.Path(__file__).parents[1] / DUMPED_DATA
    if path.exists():
        with open(path, "r") as fp:
            global transaction_history
            transaction_history = json.load(fp)


@events.test_stop.add_listener
def teardown(**kwargs) -> None:
    """Test stop Event handler"""
    pass


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
        request_type = f"`{args[1].rsplit('_')[1]}`"
        event: tp.Dict[str, tp.Any] = dict(
            task_id=task_id, request_type=request_type, task_name=f"[{kwargs.pop('req_type')}]"
        )
        locust_events_handler.init_event(**event)
        response = None
        try:
            response = func(*args, **kwargs)
            if "error" in response:
                raise web3.exceptions.ValidationError(response["error"])
            event = dict(response=response, response_length=sys.getsizeof(response), event_type="success")
        except Exception as err:
            event = dict(event_type="failure", exception=err)
            LOG.error(f"Web3 RPC call {request_type} is failed: {err} passed args: `{args}`, passed kwargs: `{kwargs}`")
        locust_events_handler.buffer[task_id].update(event)
        locust_events_handler.fire_event(task_id)
        return response

    return wrap


class ExtJsonRPCSession(apiclient.JsonRPCSession):
    """Implements extended JsonPRC api client"""

    def __init__(self, endpoint: str, pool_size: int) -> None:
        super(ExtJsonRPCSession, self).__init__(endpoint)
        adapter = requests.adapters.HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size, pool_block=True)
        self.mount("http://", adapter)
        self.mount("https://", adapter)

    @statistics_collector
    def send_rpc(self, *args, **kwargs) -> tp.Dict:
        """Extended `send_rpc` for statistics collection"""
        return super(ExtJsonRPCSession, self).send_rpc(*args, **kwargs)


class BaseEthRPCATasksSet(TaskSet):

    """Implements base behavior for task set measured by the maximum request rates
    for EIP-1898 methods implemented inside Tracer API"""

    wait_time = between(3, 5)

    _setup_class_locker = gevent.threading.Lock()
    _setup_class_done = False

    _last_consumer_id: int = 0
    """Last spawned user id
    """

    rpc_consumer_id: tp.Optional[int] = None
    """Spawned user id
    """

    _rpc_client: tp.Optional[ExtJsonRPCSession] = None
    _rpc_endpoint: tp.Optional[str] = None
    _transaction_history: tp.Optional[tp.Dict] = None

    @staticmethod
    def setup_class(environment: tp.Any = None) -> None:
        """Base initialization, run once for all users"""
        try:
            BaseEthRPCATasksSet._transaction_history = transaction_history
        except NameError:
            LOG.error(f"No transaction history found `{DUMPED_DATA}` to spawn locust users, exited.")
            exit()
        BaseEthRPCATasksSet._rpc_endpoint = credentials.get("neon_rpc", NEON_RPC) or environment.parsed_options.neon_rpc
        if not BaseEthRPCATasksSet._rpc_endpoint:
            LOG.error(
                f"Entry point to access Neon-RPC not found. "
                f"Set env `NEON_RPC` or pass `neon_rpc` to {ENV_FILE} or send via command line arguments."
            )
            exit()

    def setup(self) -> None:
        """Prepare data requirements"""
        pass

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        # setup class once
        with self._setup_class_locker:
            if not BaseEthRPCATasksSet._setup_class_done:
                self.setup_class(self.user.environment)
                BaseEthRPCATasksSet._setup_class_done = True
            BaseEthRPCATasksSet._last_consumer_id += 1
            self.rpc_consumer_id = BaseEthRPCATasksSet._last_consumer_id
            self._rpc_client = ExtJsonRPCSession(
                endpoint=self._rpc_endpoint,
                pool_size=self.user.environment.parsed_options.num_users
                or self.user.environment.runner.target_user_count,
            )
        self.setup()
        self.log = logging.getLogger("rpc-consumer[%s]" % self.rpc_consumer_id)

    def _get_random_transaction(self) -> tp.Dict:
        """Return random transaction details from transaction history"""
        key = random.choice(list(self._transaction_history.keys()))
        params = random.choice(self._transaction_history[key])
        params["from"] = key
        return params

    def _do_call(self, method: str, filter_name: str, params: tp.Optional[tp.Dict] = None) -> tp.Dict:
        tr_x = self._get_random_transaction()
        filters = {filter_name: tr_x[filter_name]}
        if params:
            filters.update(params)
        response = self._rpc_client.send_rpc(method, req_type=filter_name, params=[tr_x["from"], filters])
        self.log.info(f"Get balance by `{filter_name}`: {tr_x[filter_name]}")
        return response


@tag("getBalance")
class EthGetBalanceTasksSet(BaseEthRPCATasksSet):
    """task set measures the maximum request rate for the eth_getBalance method"""

    @tag("getBalance_by_hash")
    @task
    def task_eth_get_balance_by_hash(self) -> tp.Dict:
        """the eth_getBalance method by blockHash"""
        self._do_call(method="eth_getBalance", filter_name="blockHash")

    @tag("getBalance_by_num")
    @task
    def task_eth_get_balance_by_num(self) -> tp.Dict:
        """the eth_getBalance method by blockNumber"""
        self._do_call(method="eth_getBalance", filter_name="blockNumber")


@tag("getStorageAt")
class EthGetStorageAtTasksSet(BaseEthRPCATasksSet):
    """task set measures the maximum request rate for the eth_StorageAt method"""

    @tag("getStorage_by_hash")
    @task
    def task_eth_get_storage_by_hash(self) -> tp.Dict:
        """the eth_getStorageAt method by blockHash"""
        self._do_call(method="eth_getStorageAt", filter_name="blockHash")

    @tag("getStorage_by_num")
    @task
    def task_eth_get_storage_by_num(self) -> tp.Dict:
        """the eth_getStorageAt method by blockNumber"""
        self._do_call(method="eth_getStorageAt", filter_name="blockNumber")


class EthRPCAPICallUsers(User):
    """class represents extended ETH RPC API calls by one user"""

    tasks = {EthGetBalanceTasksSet: 1, EthGetStorageAtTasksSet: 1}
