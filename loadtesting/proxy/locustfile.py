import collections
import functools
import json
import logging
import pathlib
import random
import string
import sys
import time
import typing as tp
import uuid
from functools import lru_cache

import gevent
import requests
import solana
import web3
from locust import User, TaskSet, between, task, events, tag
from solana.keypair import Keypair

from utils import helpers
from utils.erc20wrapper import ERC20Wrapper
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

ERC20_WRAPPER_VERSION = "0.8.10"
"""ERC20 Wrapper Protocol version
"""

INCREASE_STORAGE_VERSION = "0.8.10"
"""Increase Storage Protocol version
"""

COUNTER_VERSION = "0.8.10"
"""Counter Protocol version 
"""

NEON_TOKEN_VERSION = "0.8.10"
"""Neon tokens contract version
"""

DEFAULT_DUMP_FILE = "dumped_data/transaction.json"
"""Default file name for transaction history
"""

# init global transaction history
global transaction_history
transaction_history = collections.defaultdict(list)
"""Transactions storage {account: [{blockNumber, blockHash, contractAddress},]}
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
    base_path = pathlib.Path(__file__).parent.parent.parent
    path = base_path / environment.parsed_options.credentials
    network = environment.parsed_options.host
    if not (path.exists() and path.is_file()):
        path = base_path / ENV_FILE
    with open(path, "r") as fp:
        global credentials
        f = json.load(fp)
        credentials = f.get(network, f[DEFAULT_NETWORK])


@events.test_stop.add_listener
def teardown(**kwargs) -> None:
    """Test stop event handler"""
    if transaction_history:
        dumped_path = pathlib.Path(__file__).parent.parent / DEFAULT_DUMP_FILE
        dumped_path.parents[0].mkdir(parents=True, exist_ok=True)
        with open(dumped_path, "w") as fp:
            LOG.info(f"Dumped transaction history to `{dumped_path.as_posix()}`")
            json.dump(transaction_history, fp=fp, indent=4, sort_keys=True)


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
            LOG.error(f"Web3 RPC call {request_type} is failed: {err} passed args: `{args}`, passed kwargs: `{kwargs}`")
        locust_events_handler.buffer[task_id].update(event)
        locust_events_handler.fire_event(task_id)
        return response

    return wrap


class NeonWeb3ClientExt(NeonWeb3Client):
    """Extends Neon Web3 client adds statistics metrics"""

    def __getattribute__(self, item):
        ignore_list = ["create_account", "_send_transaction"]
        try:
            attr = object.__getattribute__(self, item)
        except AttributeError:
            attr = super(NeonWeb3ClientExt, self).__getattr__(item)
        if callable(attr) and item not in ignore_list:
            attr = statistics_collector(attr)
        return attr

    def _send_transaction(self, *args, **kwargs) -> tp.Any:
        """Send transaction wrapper"""
        return super(NeonWeb3ClientExt, self).send_transaction(*args, **kwargs)

    def withdraw_tokens(self, *args, **kwargs) -> tp.Any:
        """withdraw tokens wrapper"""
        return self._send_transaction(*args, **kwargs)

    def inc_account(self, *args, **kwargs) -> tp.Any:
        """Increase account wrapper"""
        return self._send_transaction(*args, **kwargs)

    def dec_account(self, *args, **kwargs) -> tp.Any:
        """Decrease account wrapper"""
        return self._send_transaction(*args, **kwargs)


class NeonProxyTasksSet(TaskSet):
    """Implements base initialization, creates data requirements and helpers"""

    _accounts: tp.Optional[tp.List] = None
    """Cross user Accounts storage
    """
    _counter_contracts: tp.Optional[tp.Dict] = None
    """Cross user `Counter` contracts storage 
    """

    _erc20_contracts: tp.Optional[tp.Dict] = None
    """user erc20 contracts storage 
    """

    _erc20_wrapper_contracts: tp.Optional[tp.Dict] = None
    """user erc20 wrapper contracts storage 
    """

    _increase_storage_contracts: tp.Optional[tp.Dict] = None
    """Cross user `IncreaseStorage` contracts storage 
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

    _erc20wrapper_client: tp.Optional[ERC20Wrapper] = None
    _solana_client: tp.Any = None
    _web3_client: tp.Optional[NeonWeb3ClientExt] = None

    @staticmethod
    def setup_class() -> None:
        """Base initialization, run once for all users"""
        NeonProxyTasksSet._accounts = []
        NeonProxyTasksSet._counter_contracts = []
        NeonProxyTasksSet._erc20_contracts = {}
        NeonProxyTasksSet._erc20_wrapper_contracts = {}
        NeonProxyTasksSet._increase_storage_contracts = []

    def setup(self) -> None:
        """Prepare data requirements"""
        # create new account for each simulating user
        self.account = self._web3_client.create_account()
        self.task_keeps_balance()
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
            self._web3_client = NeonWeb3ClientExt(credentials["proxy_url"], credentials["network_id"], session=session)

            self._solana_client = solana.rpc.api.Client(credentials["solana_url"])
            self._erc20wrapper_client = ERC20Wrapper(
                self._web3_client, self._solana_client, credentials["evm_loader"], credentials["spl_neon_mint"]
            )
        self.setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.neon_consumer_id)

    def task_block_number(self) -> None:
        """Check the number of the most recent block"""
        self._web3_client.get_block_number()

    def task_keeps_balance(self) -> None:
        """Keeps account balance not empty"""
        if self._web3_client.get_balance(self.account.address) < 100:
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

        contract_interface = self._compile_contract_interface(name, version)
        contract_deploy_tx = self._web3_client.deploy_contract(
            account,
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
            constructor_args=constructor_args,
            gas=gas,
        )

        if not (contract_deploy_tx and contract_interface):
            return None, None

        contract = self._web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

        return contract, contract_deploy_tx

    @lru_cache(maxsize=32)
    def _compile_contract_interface(self, name, version) -> tp.Any:
        """Compile contract inteface form file"""
        return helpers.get_contract_interface(name, version)


class BaseResizingTasksSet(NeonProxyTasksSet):
    """Implements resize accounts base pipeline tasks"""

    _buffer: tp.Optional[tp.List] = None
    _contract_name: tp.Optional[str] = None
    _storage_version: tp.Optional[str] = None

    def task_deploy_contract(self) -> None:
        """Deploy contract"""
        self.log.info(f"`{self._contract_name}`: deploy contract.")
        contract, _ = self.deploy_contract(self._contract_name, self._storage_version, self.account)
        if not contract:
            self.log.error(f"`{self._contract_name}` contract deployment failed.")
            return
        self._buffer.append(contract)

    def task_resize(self, item: str) -> None:
        """Account resize"""
        if self._buffer:
            contract = random.choice(self._buffer)
            if hasattr(contract.functions, "get") and item == "dec":
                if contract.functions.get().call() == 0:
                    self.log.debug(f"Can't {item}rease account `{str(self.account.address)[:8]}`, counter is zero.")
                    return
            func = getattr(contract.functions, item)
            self.log.info(f"`{self._contract_name}`: {item}rease account `{str(contract.address)[:8]}`.")
            tx = func().buildTransaction(
                {
                    "from": self.account.address,
                    "nonce": self._web3_client.eth.get_transaction_count(self.account.address),
                    "gasPrice": self._web3_client.gas_price(),
                }
            )
            getattr(self._web3_client, f"{item}_account")(self.account, tx)
            # self._web3_client.send_transaction(self.account, tx)
            return
        self.log.debug(f"no `{self._contract_name}` contracts found, account {item}rease canceled.")


class ERC20BaseTasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    _contract_name: tp.Optional[str] = None
    _version: tp.Optional[str] = None
    _buffer: tp.Optional[tp.Dict] = None

    def _deploy_erc20_contract(self) -> "web3._utils.datatypes.Contract":
        """Deploy ERC20 contract"""
        contract, _ = self.deploy_contract(
            f"{self._contract_name}", self._version, self.account, constructor_args=[pow(10, 10)]
        )
        return contract

    def _deploy_erc20wrapper_contract(self) -> "web3._utils.datatypes.Contract":
        """Deploy SPL contract"""

        keys = Keypair.generate()
        self._solana_client.request_airdrop(keys.public_key, 10000000000)

        for _ in range(10):
            balance = self._solana_client.get_balance(keys.public_key)["result"]["value"]
            if balance == 10000000000:
                self.log.info(f"solana balance not empty, current: {balance}")
                break
            self.log.info(f"Waiting solana balance, current is: {balance}")
            time.sleep(5)
        else:
            return

        token = self._erc20wrapper_client.create_spl(keys)
        symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
        contract, address = self._erc20wrapper_client.deploy_wrapper(
            name=f"Test {symbol}", symbol=symbol, account=self.account, mint_address=token.pubkey
        )
        self._erc20wrapper_client.mint_tokens(self.account.address, keys, token.pubkey, address)
        contract = self._erc20wrapper_client.get_wrapper_contract(address)
        return contract

    def task_deploy_contract(self) -> None:
        """Deploy ERC20 or ERC20Wrapper contract"""
        self.log.info(f"Deploy `{self._contract_name.lower()}` contract.")
        contract = getattr(self, f"_deploy_{self._contract_name.lower()}_contract")()
        if not contract:
            self.log.info(f"{self._contract_name} contract deployment failed")
            return
        self._buffer.setdefault(self.account.address, set()).add(contract)

    def task_send_tokens(self) -> None:
        """Send ERC20 tokens"""
        contracts = self._buffer.get(self.account.address)
        if contracts:
            contract = random.choice(tuple(contracts))
            recipient = random.choice(self._accounts)
            self.log.info(
                f"Send `{self._contract_name.lower()}` tokens from {str(contract.address)[:8]} to {str(recipient.address)[:8]}."
            )
            tx_receipt = self._web3_client.send_erc20(self.account, recipient, 1, contract.address, abi=contract.abi)
            if tx_receipt:
                self._buffer.setdefault(recipient.address, set()).add(contract)
            # remove contracts without balance
            if contract.functions.balanceOf(self.account.address).call() < 1:
                self.log.info(f"Remove contract `{contract.address[:8]}` with empty balance from buffer.")
                contracts.remove(contract)
            return tx_receipt
        self.log.info(f"no `{self._contract_name.upper()}` contracts found, send is cancel.")


def extend_task(*attrs) -> tp.Callable:
    """Extends user task functional"""

    @functools.wraps(*attrs)
    def ext_runner(func: tp.Callable) -> tp.Callable:
        @functools.wraps(func)
        def task_wrapper(self, *args, **kwargs) -> tp.Any:
            for attr in attrs:
                getattr(self, attr)(*args, **kwargs)
            tx_receipt = func(self, *args, **kwargs)
            if tx_receipt and isinstance(tx_receipt, web3.datastructures.AttributeDict):
                transaction_history[str(tx_receipt["from"])].append(
                    {
                        "blockHash": tx_receipt["blockHash"].hex(),
                        "blockNumber": tx_receipt["blockNumber"],
                        "contractAddress": tx_receipt["contractAddress"],
                        "to": str(tx_receipt["to"])
                    }
                )

        return task_wrapper

    return ext_runner


@tag("send_neon")
class NeonTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    @task
    @extend_task("task_block_number", "task_keeps_balance")
    def task_send_neon(self) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Transferring funds to a random account"""
        # add credits to account
        recipient = random.choice(self._accounts)
        self.log.info(f"Send `neon` from {str(self.account.address)[:8]} to {str(recipient.address)[:8]}.")
        return self._web3_client.send_neon(self.account, recipient, amount=1)


@tag("erc20")
class ERC20TasksSet(ERC20BaseTasksSet):
    """Implements ERC20 base pipeline tasks"""

    def on_start(self) -> None:
        super(ERC20TasksSet, self).on_start()
        self._version = ERC20_VERSION
        self._contract_name = "ERC20"
        self._buffer = self._erc20_contracts

    @task(1)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy ERC20 contract"""
        super(ERC20TasksSet, self).task_deploy_contract()

    @task(5)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_send_erc20(self) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Send ERC20 tokens"""
        return super(ERC20TasksSet, self).task_send_tokens()


@tag("spl")
class ERC20WrappedTasksSet(ERC20BaseTasksSet):
    """Implements ERC20Wrapped base pipeline tasks"""

    def on_start(self) -> None:
        super(ERC20WrappedTasksSet, self).on_start()
        self._version = ERC20_WRAPPER_VERSION
        self._contract_name = "erc20wrapper"
        self._buffer = self._erc20_wrapper_contracts

    @task(1)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy SPL contract"""
        super(ERC20WrappedTasksSet, self).task_deploy_contract()

    @task(5)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_send_erc20(self) -> None:
        """Send ERC20 tokens"""
        super(ERC20WrappedTasksSet, self).task_send_tokens()


@tag("increase")
@tag("contract")
class IncreaseStorageTasksSet(BaseResizingTasksSet):
    """Implements `IncreaseStorage`contracts base pipeline tasks"""

    def on_start(self) -> None:
        super(IncreaseStorageTasksSet, self).on_start()
        self._buffer = self._increase_storage_contracts
        self._contract_name = "IncreaseStorage"
        self._storage_version = INCREASE_STORAGE_VERSION

    @task(1)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy IncreaseStorage contract"""
        super(IncreaseStorageTasksSet, self).task_deploy_contract()

    @task(5)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_increase_account(self) -> None:
        """Accounts increase"""
        super(IncreaseStorageTasksSet, self).task_resize("inc")


@tag("counter")
@tag("contract")
class CounterTasksSet(BaseResizingTasksSet):
    """Implements Counter contracts base pipeline tasks"""

    def on_start(self) -> None:
        super(CounterTasksSet, self).on_start()
        self._buffer = self._counter_contracts
        self._contract_name = "Counter"
        self._storage_version = COUNTER_VERSION

    @task(1)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy Counter contract"""
        super(CounterTasksSet, self).task_deploy_contract()

    @task(5)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_increase_account(self) -> None:
        """Accounts increase"""
        super(CounterTasksSet, self).task_resize("inc")

    @task(2)
    @extend_task("task_block_number", "task_keeps_balance")
    def task_decrease_account(self) -> None:
        """Accounts decrease"""
        super(CounterTasksSet, self).task_resize("dec")


@tag("withdraw")
class WithDrawTasksSet(NeonProxyTasksSet):
    """Implements withdraw tokens to Solana tasks"""

    _contract_name: str = "NeonToken"
    _version: str = NEON_TOKEN_VERSION

    @task
    @extend_task("task_block_number", "task_keeps_balance")
    def task_withdraw_tokens(self) -> None:
        """withdraw Ethereum tokens to Solana"""
        keys = Keypair.generate()
        contract_interface = self._compile_contract_interface(self._contract_name, self._version)
        erc20wrapper_address = credentials.get("neon_erc20wrapper_address")
        if erc20wrapper_address:
            self.log.info(f"withdraw tokens to Solana from {self.account.address[:8]}")
            contract = self._web3_client.eth.contract(address=erc20wrapper_address, abi=contract_interface["abi"])
            amount = self._web3_client._web3.toWei(1, "ether")
            instruction_tx = contract.functions.withdraw(bytes(keys.public_key)).buildTransaction(
                {
                    "from": self.account.address,
                    "nonce": self._web3_client.eth.get_transaction_count(self.account.address),
                    "gasPrice": self._web3_client.gas_price(),
                    "value": amount,
                }
            )
            result = self._web3_client.withdraw_tokens(self.account, instruction_tx)
            if not (result and result.get("status")):
                self.log.error(f"withdrawing tokens is failed, transaction result: {result}")
            return
        self.log.error(f"No Neon erc20wrapper address in passed credentials, can't generate contract.")


class NeonPipelineUser(User):
    """class represents a base Neon pipeline by one user"""

    wait_time = between(1, 3)
    tasks = {
        CounterTasksSet: 3,
        ERC20TasksSet: 1,
        ERC20WrappedTasksSet: 2,
        IncreaseStorageTasksSet: 2,
        NeonTasksSet: 10,
        WithDrawTasksSet: 5,
    }
