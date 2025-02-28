import os
import json
import logging
import time
import random
import base58
import pathlib
import typing as tp
import web3.types
import requests
import gevent

from dataclasses import dataclass
from functools import lru_cache

from eth_account.signers.local import LocalAccount
from solders.keypair import Keypair
from solana.rpc import commitment
from pybip39 import Mnemonic, Seed

from utils import helpers
from utils.faucet import Faucet
from utils.web3client import NeonChainWeb3Client
from utils.solana_client import SolanaClient
from gevent.pool import Pool

from utils.evm_loader import EvmLoader
from utils.neon_user import NeonUser
from utils.types import TreasuryPool
from utils.consts import LAMPORT_PER_SOL
from .events import statistics_collector, save_transaction

from locust import TaskSet, events, env

LOG = logging.getLogger(__name__)

saved_transactions = []


@events.test_stop.add_listener
def save_transactions_list(environment: env.Environment, **kwargs):
    if "SAVE_TRANSACTIONS" in os.environ:
        web3_client = NeonWeb3ClientExt(environment.credentials["proxy_url"])

        def get_solana_trx(tr):
            return tr, web3_client.get_solana_trx_by_neon(tr)

        trx = {}
        print("Start save transactions list")
        pool = Pool(10)
        tasks = [pool.spawn(get_solana_trx, t) for t in saved_transactions]
        gevent.joinall(tasks)

        for res in tasks:
            if res.value is None:
                continue
            tr, resp = res.value
            if "result" not in resp:
                print(f"Can't get solana trx from tx {tr}: {resp}")
                continue
            trx[tr] = resp["result"]
        with open(f"transactions-{random.randint(0, 1000)}.json", "w+") as f:
            json.dump(trx, f)
        print("Results saved")


def init_session(size: int = 1000) -> requests.Session:
    """init request session with extended connection pool size"""
    adapter = requests.adapters.HTTPAdapter(pool_connections=size, pool_maxsize=size, pool_block=True)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class NeonWeb3ClientExt(NeonChainWeb3Client):
    """Extends Neon Web3 client adds statistics metrics"""

    def __getattribute__(self, item):
        ignore_list = ["create_account", "_send_transaction"]
        try:
            attr = object.__getattribute__(self, item)
        except AttributeError:
            attr = super(NeonWeb3ClientExt, self).__getattr__(item)
        if callable(attr) and item not in ignore_list:
            attr = statistics_collector()(attr)
            if "SAVE_TRANSACTIONS" in os.environ:
                attr = save_transaction(saved_transactions)(attr)
        return attr


@dataclass
class NeonGlobalEnv:
    accounts = []
    neon_users = []
    counter_contracts = []
    erc20_contracts = {}
    erc20_wrapper_contracts = {}
    increase_storage_contracts = []


@events.init_command_line_parser.add_listener
def arg_parser(parser):
    """Add custom command line arguments to Locust"""
    parser.add_argument(
        "--credentials",
        type=str,
        env_var="NEON_CRED",
        default="envs.json",
        help="Relative path to environment credentials file.",
    )


@events.test_start.add_listener
def make_env_preparation(environment: env.Environment, **kwargs):
    neon = NeonGlobalEnv()
    environment.shared = neon


@events.test_start.add_listener
def load_credentials(environment: env.Environment, **kwargs):
    """Test start event handler"""
    base_path = pathlib.Path().absolute()
    path = base_path / environment.parsed_options.credentials
    network = environment.parsed_options.host or environment.host
    if not (path.exists() and path.is_file()):
        path = base_path / "envs.json"
    with open(path, "r") as fp:
        f = json.load(fp)
        environment.credentials = f[network]


class NeonProxyTasksSet(TaskSet):
    """Implements base initialization, creates data requirements and helpers"""

    faucet: tp.Optional[Faucet] = None
    bank_account = None
    account: tp.Optional[LocalAccount] = None
    solana_account: tp.Optional[Keypair] = None
    web3_client: tp.Optional[NeonWeb3ClientExt] = None
    web3_client_sol: tp.Optional[NeonWeb3ClientExt] = None
    sol_client: tp.Optional[SolanaClient] = None
    evm_loader: tp.Optional[EvmLoader] = None
    treasury_pool: tp.Optional[TreasuryPool] = None
    erc20_info: tp.Optional[dict] = {}
    network: tp.Optional[str] = None
    credentials: tp.Optional[dict] = {}

    def setup(self) -> None:
        """Prepare data requirements"""
        # create new shared account for each simulating user
        self.account = self.web3_client.create_account()
        self.check_balance()
        self.user.environment.shared.accounts.append(self.account)
        LOG.info(f"New account {self.account.address} created")

        self.neon_user = NeonUser(self.evm_loader.loader_id)
        balance = self.evm_loader.get_solana_balance(self.neon_user.solana_account.pubkey())
        if self.network not in ["devnet"]:
            if balance < 5 * LAMPORT_PER_SOL:
                self.evm_loader.request_airdrop(
                    self.neon_user.solana_account.pubkey(), 5 * LAMPORT_PER_SOL, commitment=commitment.Confirmed
                )
        self.user.environment.shared.neon_users.append(self.neon_user)
        LOG.info(f"New neon user account {self.account.address} created")

    def prepare_account(self) -> None:
        """Prepare data requirements"""
        # create new account for each simulating user
        self.account = self.web3_client.create_account()
        self.check_balance()
        LOG.info(f"New account {self.account.address} created")

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        # setup class once
        session = init_session(
            int(self.user.environment.parsed_options.num_users or self.user.environment.runner.target_user_count) * 100
        )

        self.erc20_info = self.get_erc20_info()

        self.credentials = self.user.environment.credentials
        self.network = self.user.environment.parsed_options.host or self.user.environment.host

        LOG.info(f"Create web3 client to: {self.credentials['proxy_url']}")
        self.web3_client = NeonWeb3ClientExt(self.credentials["proxy_url"])

        LOG.info(f"Create web3 sol client to: {self.credentials['proxy_url']}")
        self.web3_client_sol = NeonWeb3ClientExt(self.credentials["proxy_url"] + "/sol")

        LOG.info(f"Create solana client to: {self.credentials['solana_url']}")
        self.sol_client = SolanaClient(self.credentials["solana_url"])

        self.faucet = Faucet(self.credentials["faucet_url"], self.web3_client, session=session)
        self.evm_loader = EvmLoader(
            program_id=self.credentials["evm_loader"],
            endpoint=self.credentials["solana_url"],
            neon_chain_id=self.credentials["network_ids"]["neon"],
            sol_chain_id=self.credentials["network_ids"]["sol"],
            neon_token_mint_str=self.credentials["spl_neon_mint"],
        )

        if self.network != "local" and self.credentials["use_bank"]:
            LOG.info("Setup bank account")
            if self.network == "devnet":
                private_key = os.environ.get("BANK_PRIVATE_KEY")
            else:
                raise ValueError("set BANK_PRIVATE_KEY or BANK_PRIVATE_KEY_MAINNET env variable")
            key = base58.b58decode(private_key)
            bank_account = Keypair.from_bytes(key)
            self.bank_account = bank_account
            LOG.info(f"Create bank account: {bank_account.pubkey()}")

        sol_account_mnemonic = Mnemonic.from_phrase(self.erc20_info["solana_account_mnemonic"])
        seed = Seed(sol_account_mnemonic, self.erc20_info["solana_account_passphrase"])
        self.solana_account = Keypair.from_seed(bytes(seed)[:32])
        LOG.info(f"Create solana account: {self.solana_account.pubkey()}")

        index = 2
        self.evm_loader.create_treasury_pool_address(index)
        address = self.evm_loader.create_treasury_pool_address(index)
        index_buf = index.to_bytes(4, "little")
        balance = self.evm_loader.get_solana_balance(address)

        if balance < 5 * LAMPORT_PER_SOL:
            self.evm_loader.request_airdrop(address, 5 * LAMPORT_PER_SOL, commitment=commitment.Confirmed)
        self.treasury_pool = TreasuryPool(index, address, index_buf)

    def task_block_number(self) -> None:
        """Check the number of the most recent block"""
        self.web3_client.get_block_number()

    def check_balance(self, account: tp.Optional[LocalAccount] = None) -> None:
        """Keeps account balance not empty"""
        account = account or self.account
        balance_before = self.web3_client.get_balance(account.address)
        if balance_before < 100:
            # add credits to account
            self.faucet.request_neon(account.address, 1000)
            for _ in range(5):
                if self.web3_client.get_balance(account.address) <= balance_before:
                    time.sleep(3)
                    continue
                break
            else:
                raise AssertionError(f"Account {account.address} balance didn't change after 15 seconds")

    def deploy_contract(
        self,
        name: str,
        version: str,
        account: LocalAccount,
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

    def get_erc20_info(self):
        path = pathlib.Path().absolute() / "loadtesting/proxy/data/contract_info.json"
        with open(path, "r") as fp:
            f = json.load(fp)
        return f

    @events.test_stop.add_listener
    def refund_to_bank(self):
        if self.network != "local" and self.credentials["use_bank"]:
            balance = self.sol_client.get_balance(self.solana_account.pubkey(), commitment=commitment.Confirmed).value
            try:
                self.sol_client.send_sol(self.solana_account, self.bank_account.pubkey(), balance - 5000)
            except Exception as e:
                LOG.info(f"Failed to send sol to bank: {e}")
                LOG.info(f"Bank account private key: {self.bank_account.private_key}")
                LOG.info(f"Solana account public key: {self.solana_account.pubkey()}")
