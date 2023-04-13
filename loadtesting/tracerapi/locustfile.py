import enum
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
from dataclasses import dataclass

import gevent
import requests
import web3
from locust import User, TaskSet, between, task, events, tag

from loadtesting.proxy.common import env
from utils import apiclient
from utils.web3client import NeonWeb3Client

LOG = logging.getLogger("neon_client")

# where save dumped data
DUMPED_DATA = "dumped_data/transaction.json"

# url for history endpoint proxy
NEON_RPC = os.environ.get("NEON_TRACING_URL", "")


class RPCType(enum.Enum):
    store = ["eth_getStorageAt", "eth_call"]
    transfer = ["eth_getBalance", "eth_getTransactionCount"]

    @classmethod
    def get(cls, key: str) -> str:
        return list(
            filter(lambda i: i if key in i.value else None,
                   cls.__members__.values())
        )[0].name


@dataclass
class GlobalEnv:
    rpc_url: str = ""
    transaction_history: tp.Dict = None


@events.test_start.add_listener
def make_env_preparation(environment, **kwargs):
    global_env = GlobalEnv()
    environment.shared = global_env


@events.test_start.add_listener
def load_transaction_history(environment, **kwargs):
    # load transaction history
    path = pathlib.Path(__file__).parent / DUMPED_DATA
    if path.exists():
        with open(path, "r") as fp:
            environment.shared.transaction_history = json.load(fp)


class LocustEventHandler(object):
    """Implements custom Locust events handler"""

    def __init__(self, request_event: "EventHook") -> None:
        self.buffer: tp.Dict[str, tp.Any] = dict()
        self._request_event = request_event

    def init_event(
        self,
        task_id: str,
        request_type: str,
        task_name: tp.Optional[str] = "",
        start_time: tp.Optional[float] = None,
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
        LOG.debug(
            "- %s : %s - %sms"
            % (event["request_type"], event["event_type"], total_time)
        )


locust_events_handler = LocustEventHandler(events.request)


def statistics_collector(func: tp.Callable) -> tp.Callable:
    """Handle locust events."""

    @functools.wraps(func)
    def wrap(*args, **kwargs) -> tp.Any:
        task_id = str(uuid.uuid4())
        request_type = f"`{args[1].rsplit('_')[1]}`"
        event: tp.Dict[str, tp.Any] = dict(
            task_id=task_id,
            request_type=request_type,
            task_name=f"[{kwargs.pop('req_type')}]",
        )
        locust_events_handler.init_event(**event)
        response = None
        try:
            response = func(*args, **kwargs)
            if "error" in response:
                raise web3.exceptions.ValidationError(response["error"])
            event = dict(
                response=response,
                response_length=sys.getsizeof(response),
                event_type="success",
            )
        except Exception as err:
            event = dict(event_type="failure", exception=err)
            LOG.error(
                f"Web3 RPC call {request_type} is failed: {err} passed args: `{args}`, passed kwargs: `{kwargs}`"
            )
        locust_events_handler.buffer[task_id].update(event)
        locust_events_handler.fire_event(task_id)
        return response

    return wrap


class ExtJsonRPCSession(apiclient.JsonRPCSession):
    """Implements extended JsonPRC api client"""

    def __init__(self, endpoint: str, pool_size: int) -> None:
        super(ExtJsonRPCSession, self).__init__(endpoint)
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=pool_size, pool_maxsize=pool_size, pool_block=True
        )
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
    _transaction_history: tp.Optional[tp.Dict] = None
    credentials: tp.Optional[tp.Dict] = None

    @staticmethod
    def setup_class(environment: tp.Any = None) -> None:
        """Base initialization, run once for all users"""
        history_data = environment.shared.transaction_history
        rpc_endpoint = NEON_RPC
        if not NEON_RPC:
            rpc_endpoint = environment.credentials.get("proxy_url")
        LOG.info(f"RPC endpoint: {rpc_endpoint}")
        if not history_data:
            LOG.error(
                f"No transaction history found `{DUMPED_DATA}` to spawn locust users, exited."
            )
            sys.exit(1)
        BaseEthRPCATasksSet._transaction_history = history_data
        environment.shared.rpc_endpoint = rpc_endpoint

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
                endpoint=self.user.environment.shared.rpc_endpoint,
                pool_size=self.user.environment.parsed_options.num_users
                or self.user.environment.runner.target_user_count,
            )
        self.credentials = self.user.environment.credentials
        LOG.info(f"Create web3 client to: {self.credentials['proxy_url']}")
        self.web3_client = NeonWeb3Client(
            self.credentials["proxy_url"],
            self.credentials["network_id"],
            session=self._rpc_client,
        )
        self.log = logging.getLogger("rpc-consumer[%s]" % self.rpc_consumer_id)

    def _get_random_transaction(self, key: str) -> tp.Dict:
        """Return random transaction details from transaction history"""
        transactions = self._transaction_history[RPCType.get(key)]
        key = random.choice(list(transactions.keys()))
        params = random.choice(transactions[key])
        params["from"] = key
        return params

    def _check_transfer(self, transfer_info):
        if transfer_info:
            assert float(transfer_info['sender_balance_before']) - \
                float(transfer_info['sender_balance_after']
                      ) >= float(transfer_info['amount'])
            assert float(transfer_info['recipient_balance_after']) - \
                float(transfer_info['recipient_balance_before']) <= float(
                    transfer_info['amount'])

    def _do_call(
        self,
        method: str,
        req_type: str,
        args: tp.Optional[tp.List] = None,
        kwargs: tp.Optional[tp.Dict] = None,
    ) -> tp.Dict:
        transaction = self._get_random_transaction(method)
        self._check_transfer(transaction['additional_info'])
        if not args:
            args = []
        elif not isinstance(args, list):
            args = [args]
        kwargs = kwargs or {}
        kwargs.update({req_type: transaction[req_type]})
        args.append(kwargs)
        args.insert(0, transaction["to"])
        response = self._rpc_client.send_rpc(
            method, req_type=req_type, params=args)
        self.log.info(
            f"Call {method}, get data by `{req_type}`: {transaction[req_type]}. Response: {response}"
        )
        return response


@tag("getBalance")
class EthGetBalanceTasksSet(BaseEthRPCATasksSet):
    """task set measures the maximum request rate for the eth_getBalance method"""

    @tag("getBalance_by_hash")
    @task
    def task_eth_get_balance_by_hash(self) -> tp.Dict:
        """the eth_getBalance method by blockHash"""
        self._do_call(method="eth_getBalance", req_type="blockHash")

    @tag("getBalance_by_num")
    @task
    def task_eth_get_balance_by_num(self) -> tp.Dict:
        """the eth_getBalance method by blockNumber"""
        self._do_call(method="eth_getBalance", req_type="blockNumber")


@tag("getTransactionCount")
class EthGetTransactionCountTasksSet(BaseEthRPCATasksSet):
    """task set measures the maximum request rate for the eth_getTransactionCount method"""

    @tag("getTransactionCount_by_hash")
    @task
    def task_eth_get_transaction_count_by_hash(self) -> tp.Dict:
        """the eth_getTransactionCount method by blockHash"""
        self._do_call(method="eth_getTransactionCount", req_type="blockHash")

    @tag("getTransactionCount_by_num")
    @task
    def task_eth_get_transaction_count_by_num(self) -> tp.Dict:
        """the eth_getTransactionCount method by blockNumber"""
        self._do_call(method="eth_getTransactionCount", req_type="blockNumber")


@tag("getStorageAt")
class EthGetStorageAtTasksSet(BaseEthRPCATasksSet):
    """task set measures the maximum request rate for the eth_getStorageAt method"""

    @tag("getStorageAt_by_hash")
    @task
    def task_eth_get_storage_at_by_hash(self) -> tp.Dict:
        """the eth_getStorageAt method by blockHash"""
        response = self._do_call(
            method="eth_getStorageAt", req_type="blockHash", args="0x0")
        assert response['result'] != '0x0'

    @tag("getStorageAt_by_num")
    @task
    def task_eth_get_storage_at_by_num(self) -> tp.Dict:
        """the eth_getStorageAt method by blockNumber"""
        response = self._do_call(
            method="eth_getStorageAt", req_type="blockNumber", args="0x0")
        assert response['result'] != '0x0'


@tag("call")
class EthCall(BaseEthRPCATasksSet):
    """task set measures the maximum request rate for the eth_call method"""

    _deploy_contract_locker = gevent.threading.Lock()
    _deploy_contract_done = False
    _contract: tp.Optional["web3._utils.datatypes.Contract"] = None
    method = "eth_call"

    def deploy_contract(self):
        """Deploy once for all spawned users"""
        EthCall._deploy_contract_done = True
        transaction = self._get_random_transaction(self.method)
        contract = self.web3_client.eth.contract(
            address=transaction["contract"]["address"],
            abi=transaction["contract"]["abi"],
        )
        self.log.info(f"Contract deployed {contract}.")
        if not contract:
            self.log.error(f"contract deployment failed.")
            EthCall._deploy_contract_done = False
            return
        EthCall._contract = contract

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        super(EthCall, self).on_start()
        # setup class once
        with self._deploy_contract_locker:
            if not EthCall._deploy_contract_done:
                self.deploy_contract()

    def _do_call(self, method: str, req_type: str) -> None:
        """Store random int to contract"""
        self.log.info(
            f"Call `retrieve` method from {self._contract.address} contract by `{method}`."
        )
        transaction = self._get_random_transaction(self.method)
        tx = self._contract.functions.retrieve().build_transaction(
            {
                "nonce": self.web3_client.eth.get_transaction_count(
                    transaction["from"]
                ),
                "gasPrice": self.web3_client.gas_price(),
            }
        )

        tx_call_obj = {
            "from": transaction["from"],
            "to": transaction["to"],
            "value": hex(tx["value"]),
            "gas": hex(tx["gas"]),
            "gasPrice": hex(tx["gasPrice"]),
            "data": tx["data"],
        }
        response = self._rpc_client.send_rpc(
            method,
            req_type=req_type,
            params=[tx_call_obj, {req_type: transaction[req_type]}],
        )
        self.log.info(
            f"Call {method}, get data by `{req_type}`: {transaction[req_type]}. Response: {response}"
        )
        return response

    @tag("call_by_hash")
    @task
    def task_eth_call_by_hash(self) -> tp.Dict:
        """the eth_call method by blockHash"""
        response = self._do_call(method="eth_call", req_type="blockHash")
        assert response['result'] != '0x0'

    @tag("call_by_num")
    @task
    def task_eth_call_by_num(self) -> tp.Dict:
        """the eth_call method by blockNumber"""
        response = self._do_call(method="eth_call", req_type="blockNumber")
        assert response['result'] != '0x0'


class EthRPCAPICallUsers(User):
    """class represents extended ETH RPC API calls by one user"""

    tasks = {
        EthGetBalanceTasksSet: 1,
        EthGetTransactionCountTasksSet: 1,
        EthGetStorageAtTasksSet: 1,
        EthCall: 1,
    }
