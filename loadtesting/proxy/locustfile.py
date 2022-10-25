import functools
import json
import logging
import os
import pathlib
import random
import shutil
import string
import subprocess
import sys
import time
import typing as tp
import uuid
from dataclasses import dataclass
from functools import lru_cache

import locust.env
import requests
import tabulate
import web3
from locust import TaskSet, User, events, tag, task
from locust.runners import WorkerRunner

from solana.keypair import Keypair

from utils import helpers, operator
from utils.erc20wrapper import ERC20Wrapper
from utils.faucet import Faucet
from utils.web3client import NeonWeb3Client

LOG = logging.getLogger("neon_loadtest")

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

UNISWAP_REPO_URL = "https://github.com/gigimon/Uniswap-V2-NEON.git"
UNISWAP_TMP_DIR = "/tmp/uniswap-neon"
MAX_UINT_256 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF


@dataclass
class NeonGlobalEnv:
    accounts = []
    counter_contracts = []
    erc20_contracts = {}
    erc20_wrapper_contracts = {}
    increase_storage_contracts = []


def execute_before(*attrs) -> tp.Callable:
    """Extends user task functional"""

    @functools.wraps(*attrs)
    def ext_runner(func: tp.Callable) -> tp.Callable:
        @functools.wraps(func)
        def task_wrapper(self, *args, **kwargs) -> tp.Any:
            for attr in attrs:
                getattr(self, attr)(*args, **kwargs)
            return func(self, *args, **kwargs)

        return task_wrapper

    return ext_runner


def init_session(size: int) -> requests.Session:
    """init request session with extended connection pool size"""
    adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100, pool_block=True)
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
def make_env_preparation(environment, **kwargs):
    neon = NeonGlobalEnv()
    environment.shared = neon


@events.test_start.add_listener
def load_credentials(environment, **kwargs):
    """Test start event handler"""
    base_path = pathlib.Path(__file__).parent.parent.parent
    path = base_path / environment.parsed_options.credentials
    network = environment.parsed_options.host
    if not (path.exists() and path.is_file()):
        path = base_path / ENV_FILE
    with open(path, "r") as fp:
        f = json.load(fp)
        environment.credentials = f[network]


def get_token_balance(op: operator.Operator) -> tp.Dict:
    """Return tokens balance"""
    return dict(neon=op.get_neon_balance(), sol=op.get_solana_balance())


@events.test_start.add_listener
def operator_economy_pre_balance(environment, **kwargs):
    if isinstance(environment.runner, WorkerRunner):
        return
    op = operator.Operator(
        environment.credentials["proxy_url"],
        environment.credentials["solana_url"],
        environment.credentials["network_id"],
        environment.credentials["operator_neon_rewards_address"],
        environment.credentials["spl_neon_mint"],
        environment.credentials["operator_keys"],
        web3_client=NeonWeb3Client(
            environment.credentials["proxy_url"], environment.credentials["network_id"], session=requests.Session()
        ),
    )
    environment.op = op
    environment.pre_balance = get_token_balance(op)


@events.test_stop.add_listener
def operator_economy_balance(environment, **kwargs):
    if isinstance(environment.runner, WorkerRunner):
        return
    balance = get_token_balance(environment.op)
    operator_balance = tabulate.tabulate(
        [
            ["NEON", environment.pre_balance["neon"], balance["neon"]],
            ["SOL", environment.pre_balance["sol"], balance["sol"]],
        ],
        headers=["token", "on start balance", "os stop balance"],
        tablefmt="fancy_outline",
        numalign="right",
        floatfmt=".2f",
    )
    LOG.info(f"\n{10*'_'} Operator balance {10*'_'}\n{operator_balance}\n")


@events.test_start.add_listener
def deploy_uniswap(environment: "locust.env.Environment", **kwargs):
    # 1. git clone repo with uniswap
    # 2. deploy 3 erc20 contracts
    # 3. deploy uniswap and create pairs
    # 4. make liquidities

    if environment.parsed_options.exclude_tags and "uniswap" in environment.parsed_options.exclude_tags:
        return

    if environment.parsed_options.tags and "uniswap" not in environment.parsed_options.tags:
        return
    LOG.info("Start deploy Uniswap")
    base_cwd = os.getcwd()
    uniswap_path = pathlib.Path(UNISWAP_TMP_DIR)
    if not uniswap_path.exists():
        shutil.rmtree(UNISWAP_TMP_DIR, ignore_errors=True)
        subprocess.call(f"git clone {UNISWAP_REPO_URL} {uniswap_path}", shell=True)
        os.chdir(uniswap_path)
        subprocess.call("npm install", shell=True)
    os.chdir(uniswap_path)

    neon_client = NeonWeb3Client(environment.credentials["proxy_url"], environment.credentials["network_id"])
    faucet = Faucet(environment.credentials["faucet_url"])

    eth_account = neon_client.create_account()
    faucet.request_neon(eth_account.address, 10000)

    erc20_contracts = {"tokenA": "", "tokenB": "", "tokenC": "", "weth": ""}
    LOG.info("Deploy ERC20 tokens for Uniswap")
    for token in erc20_contracts:
        erc_contract, _ = neon_client.deploy_and_get_contract(
            str(uniswap_path / "contracts/v2-core/test/ERC20.sol"),
            account=eth_account,
            version="0.5.16",
            constructor_args=[web3.Web3.toWei(10000000000, "ether")],
        )
        erc20_contracts[token] = erc_contract
    LOG.info("Deploy Uniswap factory")
    uniswap2_factory, _ = neon_client.deploy_and_get_contract(
        str(uniswap_path / "contracts/v2-core/UniswapV2Factory.sol"),
        account=eth_account,
        version="0.5.16",
        constructor_args=[eth_account.address],
    )
    LOG.info("Deploy Uniswap router")
    uniswap2_router, _ = neon_client.deploy_and_get_contract(
        str(uniswap_path / "contracts/v2-periphery/UniswapV2Router02.sol"),
        account=eth_account,
        version="0.6.6",
        import_remapping={"@uniswap": str(uniswap_path / "node_modules/@uniswap")},
        constructor_args=[uniswap2_factory.address, erc20_contracts["weth"].address],
    )
    LOG.info(f'Create pair1 {erc20_contracts["tokenA"].address} <-> {erc20_contracts["tokenB"].address}')
    pair1_transaction = uniswap2_factory.functions.createPair(
        erc20_contracts["tokenA"].address, erc20_contracts["tokenB"].address
    ).buildTransaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
        }
    )
    neon_client.send_transaction(eth_account, pair1_transaction)
    LOG.info(f'Create pair2 {erc20_contracts["tokenB"].address} <-> {erc20_contracts["tokenC"].address}')
    pair2_transaction = uniswap2_factory.functions.createPair(
        erc20_contracts["tokenB"].address, erc20_contracts["tokenC"].address
    ).buildTransaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
        }
    )
    neon_client.send_transaction(eth_account, pair2_transaction)

    pair1_address = uniswap2_factory.functions.getPair(
        erc20_contracts["tokenA"].address, erc20_contracts["tokenB"].address
    ).call()
    pair2_address = uniswap2_factory.functions.getPair(
        erc20_contracts["tokenB"].address, erc20_contracts["tokenC"].address
    ).call()

    pair_contract_interface = helpers.get_contract_interface(
        str(uniswap_path / "contracts/v2-core/UniswapV2Pair.sol"), version="0.5.16"
    )

    pair1_contract = neon_client.eth.contract(address=pair1_address, abi=pair_contract_interface["abi"])
    pair2_contract = neon_client.eth.contract(address=pair2_address, abi=pair_contract_interface["abi"])

    for token in erc20_contracts:
        c = erc20_contracts[token]
        tr = c.functions.approve(uniswap2_router.address, MAX_UINT_256).buildTransaction(
            {
                "from": eth_account.address,
                "nonce": neon_client.eth.get_transaction_count(eth_account.address),
                "gasPrice": neon_client.gas_price(),
            }
        )
        neon_client.send_transaction(eth_account, tr)

    LOG.info("Add liquidities to pools")
    tr = uniswap2_router.functions.addLiquidity(
        erc20_contracts["tokenA"].address,
        erc20_contracts["tokenB"].address,
        web3.Web3.toWei(1000000, "ether"),
        web3.Web3.toWei(1000000, "ether"),
        0,
        0,
        eth_account.address,
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
    ).buildTransaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
        }
    )
    neon_client.send_transaction(eth_account, tr)
    tr = uniswap2_router.functions.addLiquidity(
        erc20_contracts["tokenB"].address,
        erc20_contracts["tokenC"].address,
        web3.Web3.toWei(1000000, "ether"),
        web3.Web3.toWei(1000000, "ether"),
        0,
        0,
        eth_account.address,
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
    ).buildTransaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
        }
    )
    neon_client.send_transaction(eth_account, tr)
    os.chdir(base_cwd)
    environment.uniswap = {
        "signer": eth_account,
        "router": uniswap2_router,
        "factory": uniswap2_factory,
        "pair1": pair1_contract,
        "pair2": pair2_contract,
    }
    environment.uniswap.update(erc20_contracts)


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


def statistics_collector(name: tp.Optional[str] = None) -> tp.Callable:
    """Handle locust events."""

    def decor(func: tp.Callable) -> tp.Callable:
        @functools.wraps(func)
        def wrap(*args, **kwargs) -> tp.Any:
            task_id = str(uuid.uuid4())
            if name:
                request_type = name
            else:
                request_type = f"{func.__name__.replace('_', ' ').title()}"
            event = dict(task_id=task_id, request_type=request_type)
            locust_events_handler.init_event(**event)
            response = None
            try:
                response = func(*args, **kwargs)
                event = dict(response=response, response_length=sys.getsizeof(response), event_type="success")
            except Exception as err:
                event = dict(event_type="failure", exception=err)
                LOG.error(
                    f"Web3 RPC call {request_type} is failed: {err} passed args: `{args}`, passed kwargs: `{kwargs}`"
                )
            locust_events_handler.buffer[task_id].update(event)
            locust_events_handler.fire_event(task_id)
            return response

        return wrap

    return decor


class NeonWeb3ClientExt(NeonWeb3Client):
    """Extends Neon Web3 client adds statistics metrics"""

    def __getattribute__(self, item):
        ignore_list = ["create_account", "_send_transaction"]
        try:
            attr = object.__getattribute__(self, item)
        except AttributeError:
            attr = super(NeonWeb3ClientExt, self).__getattr__(item)
        if callable(attr) and item not in ignore_list:
            attr = statistics_collector()(attr)
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

    def store_randint(self, *args, **kwargs) -> tp.Any:
        return self._send_transaction(*args, **kwargs)


class NeonProxyTasksSet(TaskSet):
    """Implements base initialization, creates data requirements and helpers"""

    faucet: tp.Optional[Faucet] = None
    account: tp.Optional["eth_account.signers.local.LocalAccount"] = None
    web3_client: tp.Optional[NeonWeb3ClientExt] = None

    def setup(self) -> None:
        """Prepare data requirements"""
        # create new account for each simulating user
        self.account = self.web3_client.create_account()
        self.task_keeps_balance()
        self.user.environment.shared.accounts.append(self.account)
        LOG.info(f"New account {self.account.address} created")

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        # setup class once
        session = init_session(
            self.user.environment.parsed_options.num_users or self.user.environment.runner.target_user_count
        )
        self.credentials = self.user.environment.credentials
        self.faucet = Faucet(self.credentials["faucet_url"], session=session)
        LOG.info(f"Create web3 client to: {self.credentials['proxy_url']}")
        self.web3_client = NeonWeb3ClientExt(
            self.credentials["proxy_url"], self.credentials["network_id"], session=session
        )
        self.setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])

    def task_block_number(self) -> None:
        """Check the number of the most recent block"""
        self.web3_client.get_block_number()

    def task_keeps_balance(self, account: tp.Optional["eth_account.signers.local.LocalAccount"] = None) -> None:
        """Keeps account balance not empty"""
        account = account or self.account
        if self.web3_client.get_balance(account.address) < 100:
            # add credits to account
            self.faucet.request_neon(account.address, 1000)

    def deploy_contract(
        self,
        name: str,
        version: str,
        account: "eth_account.signers.local.LocalAccount",
        constructor_args: tp.Optional[tp.Any] = None,
        gas: tp.Optional[int] = 0,
        contract_name: tp.Optional[str] = None,
    ) -> "web3._utils.datatypes.Contract":
        """contract deployments"""

        contract_interface = self._compile_contract_interface(name, version, contract_name)
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

    @lru_cache(maxsize=32)
    def _compile_contract_interface(self, name, version, contract_name: tp.Optional[str] = None) -> tp.Any:
        """Compile contract inteface form file"""
        return helpers.get_contract_interface(name, version, contract_name=contract_name)


class BaseResizingTasksSet(NeonProxyTasksSet):
    """Implements resize accounts base pipeline tasks"""

    _buffer: tp.Optional[tp.List] = None
    contract_name: tp.Optional[str] = None
    version: tp.Optional[str] = None

    @task(1)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy contract"""
        self.log.info(f"`{self.contract_name}`: deploy contract.")
        contract, _ = self.deploy_contract(self.contract_name, self.version, self.account)
        if not contract:
            self.log.error(f"`{self.contract_name}` contract deployment failed.")
            return
        self._buffer.append(contract)

    def task_resize(self, item: str) -> None:
        """Account resize"""
        if self._buffer:
            contract = random.choice(self._buffer)
            if hasattr(contract.functions, "get") and item == "dec":
                if contract.functions.get().call() <= 1:
                    self.log.info(
                        f"Can't {item}rease contract `{str(contract.address)[:8]}`, counter is zero. Do increase."
                    )
                    item = "inc"
            func = getattr(contract.functions, item)
            self.log.info(f"`{self.contract_name}`: {item}rease in contract `{str(contract.address)[:8]}`.")
            try:
                tx = func().buildTransaction(
                    {
                        "from": self.account.address,
                        "nonce": self.web3_client.eth.get_transaction_count(self.account.address),
                        "gasPrice": self.web3_client.gas_price(),
                    }
                )
                getattr(self.web3_client, f"{item}_account")(self.account, tx)
            except web3.exceptions.ContractLogicError as e:
                if "execution reverted" not in e.args:
                    raise
            return
        self.log.debug(f"no `{self.contract_name}` contracts found, account {item}rease canceled.")


class ERC20BaseTasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    contract_name: tp.Optional[str] = None
    version: tp.Optional[str] = None
    _buffer: tp.Optional[tp.Dict] = None
    _erc20wrapper_client: tp.Optional[ERC20Wrapper] = None
    _solana_client: tp.Any = None

    def on_start(self) -> None:
        super(ERC20BaseTasksSet, self).on_start()

    def task_deploy_contract(self) -> None:
        """Deploy ERC20 or ERC20Wrapper contract"""
        self.log.info(f"Deploy `{self.contract_name.lower()}` contract.")
        # contract = self.deploy_contract(self.contract_name, self.version, self.account, [pow(10, 10)])
        amount_range = pow(10, 15)
        amount = random.randint(amount_range, amount_range + pow(10, 3))
        contract = getattr(self, f"_deploy_{self.contract_name.lower()}_contract")(ammount=amount)
        if not contract or contract[0] is None:
            self.log.info(f"{self.contract_name} contract deployment failed {contract[1]}")
            return
        acc_balances = self._buffer.get(self.account.address, {})
        acc_balances[contract[0].address] = {"contract": contract[0], "amount": amount}
        self._buffer[self.account.address] = acc_balances

    def task_send_tokens(self) -> None:
        """Send ERC20/ERC20Wrapped tokens"""
        contracts = self._buffer.get(self.account.address)

        if contracts:
            contract_address = random.choice(list(contracts.keys()))
            # if contracts[contract_address]["amount"] <= 1:
            #    return self.task_send_tokens()
            contract = contracts[contract_address]["contract"]
            recipient = random.choice(self.user.environment.shared.accounts)
            self.log.info(
                f"Send `{self.contract_name.lower()}` tokens from contract {str(contract.address)[-8:]} to {str(recipient.address)[-8:]}."
            )
            tx_receipt = self.web3_client.send_erc20(self.account, recipient, 1, contract.address, abi=contract.abi)
            if tx_receipt:
                # self._buffer.setdefault(recipient.address, set()).add(contract)
                # tx_receipt = dict(tx_receipt)
                tx_receipt = dict(tx_receipt)  # AttributeDict -> dict
                tx_receipt["contractAddress"] = contract.address
                contract_amount = self._buffer[self.account.address][contract.address]["amount"]
                if contract_amount < 1:
                    del self._buffer[self.account.address][contract.address]
                else:
                    contract_amount -= 1
                recep_balances = self._buffer.get(recipient.address, {})
                recep_contract = recep_balances.get(contract.address, {})
                if not recep_contract:
                    recep_contract["contract"] = contract
                    recep_contract["amount"] = 0
                recep_contract["amount"] += 1
                self._buffer[recipient.address] = recep_balances
            return tx_receipt
        self.log.info(f"no `{self.contract_name.upper()}` contracts found, send is cancel.")

    # def task_deploy_contract(self) -> None:
    #    """Deploy ERC20/ERCWrapped contract"""
    #
    #    self.log.info(f"Deploy `{self.contract_name.lower()}` contract.")
    #    contract = getattr(self, f"_deploy_{self.contract_name.lower()}_contract")()
    #    if not contract:
    #        self.log.info(f"{self.contract_name} contract deployment failed")
    #        return
    #    self._buffer.setdefault(self.account.address, set()).add(contract)

    def _deploy_erc20_contract(self, amount: int) -> "web3._utils.datatypes.Contract":
        """Deploy ERC20 contract"""
        contract, _ = self.deploy_contract(self.contract_name, self.version, self.account, constructor_args=[amount])
        return contract

    def _deploy_erc20wrapper_contract(self, amount: int) -> "web3._utils.datatypes.Contract":
        """Deploy ERC20Wrapped contract"""
        symbol = "".join(random.sample(string.ascii_uppercase, 3))
        erc20wrapper_client = ERC20Wrapper(
            self.web3_client, self.faucet, name=f"Test {symbol}", symbol=symbol, account=self.account
        )
        # amount_range = pow(10, 15)
        erc20wrapper_client.mint_tokens(
            # self.account, self.account.address, amount=random.randint(amount_range, amount_range + pow(10, 3))
            self.account,
            self.account.address,
            amount=amount,
        )
        return erc20wrapper_client.contract


@tag("send_neon")
class NeonTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    @task(1)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_send_neon(self) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Transferring funds to a random account"""
        # add credits to account
        recipient = random.choice(self.user.environment.shared.accounts)
        self.log.info(f"Send `neon` from {str(self.account.address)[-8:]} to {str(recipient.address)[-8:]}.")
        return self.web3_client.send_neon(self.account, recipient, amount=1)


@tag("erc20")
class ERC20TasksSet(ERC20BaseTasksSet):
    """Implements ERC20 base pipeline tasks"""

    def on_start(self) -> None:
        super(ERC20TasksSet, self).on_start()
        self.version = ERC20_VERSION
        self.contract_name = "ERC20"
        self._buffer = self.user.environment.shared.erc20_contracts

    @task(2)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy ERC20 contract"""
        super(ERC20TasksSet, self).task_deploy_contract()

    @task(6)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_send_erc20(self) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Send ERC20 tokens"""
        return super(ERC20TasksSet, self).task_send_tokens()


@tag("SPL")
class ERC20SPLTasksSet(ERC20BaseTasksSet):
    """Implements ERC20Wrapped base pipeline tasks"""

    def on_start(self) -> None:
        super(ERC20SPLTasksSet, self).on_start()
        self.version = ERC20_WRAPPER_VERSION
        self.contract_name = "erc20wrapper"
        self._buffer = self.user.environment.shared.erc20_wrapper_contracts

    @task(6)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_send_erc20_wrapped(self) -> None:
        """Send ERC20 tokens"""
        return super(ERC20SPLTasksSet, self).task_send_tokens()

    @task(2)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy ERC20Wrapper contract"""
        super(ERC20SPLTasksSet, self).task_deploy_contract()


@tag("counter")
@tag("contract")
class CounterTasksSet(BaseResizingTasksSet):
    """Implements Counter contracts base pipeline tasks"""

    def on_start(self) -> None:
        super(CounterTasksSet, self).on_start()
        self._buffer = self.user.environment.shared.counter_contracts
        self.contract_name = "Counter"
        self.version = COUNTER_VERSION

    @task(4)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_increase_counter(self) -> None:
        """Accounts increase"""
        super(CounterTasksSet, self).task_resize("inc")

    @task(2)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_decrease_counter(self) -> None:
        """Accounts decrease"""
        super(CounterTasksSet, self).task_resize("dec")


@tag("withdraw")
class WithDrawTasksSet(NeonProxyTasksSet):
    """Implements withdraw tokens to Solana tasks"""

    _contract_name: str = "NeonToken"
    _version: str = NEON_TOKEN_VERSION

    @task
    @execute_before("task_block_number", "task_keeps_balance")
    def task_withdraw_tokens(self) -> None:
        """withdraw Ethereum tokens to Solana"""
        keys = Keypair.generate()
        contract_interface = self._compile_contract_interface(self.contract_name, self.version)
        erc20wrapper_address = self.credentials.get("neon_erc20wrapper_address")
        if erc20wrapper_address:
            self.log.info(f"withdraw tokens to Solana from {self.account.address[:8]}")
            contract = self.web3_client.eth.contract(address=erc20wrapper_address, abi=contract_interface["abi"])
            amount = self.web3_client._web3.toWei(1, "ether")
            instruction_tx = contract.functions.withdraw(bytes(keys.public_key)).buildTransaction(
                {
                    "from": self.account.address,
                    "nonce": self.web3_client.eth.get_transaction_count(self.account.address),
                    "gasPrice": self.web3_client.gas_price(),
                    "value": amount,
                }
            )
            result = self.web3_client.withdraw_tokens(self.account, instruction_tx)
            if not (result and result.get("status")):
                self.log.error(f"withdrawing tokens is failed, transaction result: {result}")
            return
        self.log.error(f"No Neon erc20wrapper address in passed credentials, can't generate contract.")


@tag("uniswap")
class UniswapTransaction(NeonProxyTasksSet):
    def on_start(self) -> None:
        super(UniswapTransaction, self).on_start()
        signer = self.user.environment.uniswap["signer"]
        token_a = self.user.environment.uniswap["tokenA"]
        token_b = self.user.environment.uniswap["tokenB"]
        token_c = self.user.environment.uniswap["tokenC"]

        for token in [token_a, token_b, token_c]:
            self.log.info(f"Transfer erc token to account: {self.account.address}")
            trx = token.functions.transfer(self.account.address, web3.Web3.toWei(1000, "ether")).buildTransaction(
                {
                    "from": signer.address,
                    "nonce": self.web3_client.eth.get_transaction_count(signer.address),
                    "gasPrice": self.web3_client.gas_price(),
                }
            )
            self.web3_client.send_transaction(signer, trx)

            self.log.info(f"Approve token by account {self.account.address}")
            trx = token.functions.approve(
                self.user.environment.uniswap["router"].address, MAX_UINT_256
            ).buildTransaction(
                {
                    "from": self.account.address,
                    "nonce": self.web3_client.get_nonce(self.account.address),
                    "gasPrice": self.web3_client.gas_price(),
                }
            )
            self.web3_client.send_transaction(self.account, trx)

    def _send_swap_trx(self, trx):
        self.web3_client.send_transaction(self.account, trx, gas_multiplier=1.1)

    @statistics_collector("Direct swap")
    def _send_direct_swap_trx(self, trx):
        return self._send_swap_trx(trx)

    @statistics_collector("Swap 2 pools")
    def _send_2pools_swap_trx(self, trx):
        return self._send_swap_trx(trx)

    @task
    def task_swap_direct(self):
        router = self.user.environment.uniswap["router"]
        token_a = self.user.environment.uniswap["tokenA"]
        token_b = self.user.environment.uniswap["tokenB"]
        self.log.info("Swap token direct")
        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.toWei(1, "ether"),
            0,
            random.sample([token_a.address, token_b.address], 2),
            self.account.address,
            MAX_UINT_256,
        ).buildTransaction(
            {
                "from": self.account.address,
                "nonce": self.web3_client.get_nonce(self.account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        self._send_direct_swap_trx(swap_trx)

    @task
    def task_swap_two_pools(self):
        router = self.user.environment.uniswap["router"]
        token_a = self.user.environment.uniswap["tokenA"]
        token_b = self.user.environment.uniswap["tokenB"]
        token_c = self.user.environment.uniswap["tokenC"]
        self.log.info("Swap token via 2 pools")
        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.toWei(1, "ether"),
            0,
            [token_a.address, token_b.address, token_c.address],
            self.account.address,
            MAX_UINT_256,
        ).buildTransaction(
            {
                "from": self.account.address,
                "nonce": self.web3_client.get_nonce(self.account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        self._send_2pools_swap_trx(swap_trx)


class NeonPipelineUser(User):
    """Class represents a base Neon pipeline by one user"""

    tasks = {
        CounterTasksSet: 3,
        ERC20TasksSet: 1,
        ERC20SPLTasksSet: 2,
        NeonTasksSet: 10,
        # WithDrawTasksSet: 5,  Disable this, because withdraw instruction changed
        UniswapTransaction: 5,
    }
