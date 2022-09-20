# coding: utf-8
"""
Created on 2022-08-18
@author: Eugeny Kurkovich
"""
import base64
import functools
import json
import time
import logging
import os
import pathlib
import random
import typing as tp
from dataclasses import dataclass

import gevent
import gevent.queue
import requests

import web3
import eth_account
from eth_keys import keys as eth_keys
from locust import TaskSet, User, events, task, FastHttpUser
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.api import Client as SolanaClient
from solana.rpc.providers import http
from solana.rpc.types import TxOpts
from solana.system_program import SYS_PROGRAM_ID
from solana.blockhash import Blockhash
from solana.transaction import AccountMeta, TransactionInstruction

from loadtesting.synthetic import helpers
from ui.libs import try_until
from utils import faucet

LOG = logging.getLogger("sol-client")

DEFAULT_NETWORK = os.environ.get("NETWORK", "night-stand")
"""Default test environment name
"""

ENV_FILE = "envs.json"
""" Default environment credentials storage 
"""

DEFAULT_NEON_AMOUNT = 10000
"""Default airdropped NEON amount 
"""

DEFAULT_SOL_AMOUNT = 1000000 * 10 ** 9
"""Default airdropped SOL amount 
"""

CWD = pathlib.Path(__file__).parent
"""Current working directory
"""

BASE_PATH = CWD.parent.parent
"""Project root directory
"""

SYS_INSTRUCT_ADDRESS = "Sysvar1nstructions1111111111111111111111111"

ACCOUNT_SEED_VERSION = b'\1'
ACCOUNT_ETH_BASE = int(web3.eth.Account.create().privateKey.hex(), 16)

PREPARED_USERS_COUNT = 2


def init_session(size: int) -> requests.Session:
    """init request session with extended connection pool size"""
    adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100, pool_block=False)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def handle_failed_requests(func: tp.Callable) -> tp.Callable:
    """Extends solana client functional"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> tp.Any:
        resp = func(self, *args, **kwargs)
        if resp.get("error"):
            raise AssertionError(
                f"Request `{args[0]}` is failed! [{resp['error']['code']}]:{resp['error']['message']}.\n{args[1:]}"
            )
        return resp
    return wrapper


class ExtendedHTTPProvider(http.HTTPProvider):
    @handle_failed_requests
    def make_request(self, *args, **kwargs) -> tp.Dict:
        return super(ExtendedHTTPProvider, self).make_request(*args, **kwargs)


class OperatorAccount(Keypair):
    """Implements operator Account"""

    def __init__(self, key_id: tp.Optional[int] = "") -> None:
        self._path = CWD / f"operator-keypairs/id{key_id}.json"
        if not self._path.exists():
            raise FileExistsError(f"Operator key `{self._path}` not exists")
        with open(self._path) as fd:
            key = json.load(fd)[:32]
        super(OperatorAccount, self).__init__(key)

    def get_path(self) -> str:
        """Return operator key storage path"""
        return self._path.as_posix()

    @property
    def eth_address(self) -> str:
        return eth_keys.PrivateKey(self.secret_key[:32]).public_key.to_address()


class SOLClient:
    """"""

    def __init__(self, credentials: tp.Dict, session: tp.Optional[requests.Session], timeout: float = 1) -> None:
        self._web3 = web3.Web3()
        self._faucet = faucet.Faucet(credentials["faucet_url"], session)
        self._evm_loader = PublicKey(credentials["evm_loader"])
        self._client = SolanaClient()
        self._client._provider = ExtendedHTTPProvider(credentials["solana_url"], timeout=timeout)
        self._credentials = credentials

    def __getattr__(self, item) -> tp.Any:
        return getattr(self._client, item)

    def ether2solana(self, eth_address: tp.Union[str, "eth_account.account.LocalAccount"]) -> tp.Tuple[PublicKey, int]:
        if isinstance(eth_address, (eth_account.account.LocalAccount, eth_account.signers.local.LocalAccount)):
            eth_address = eth_address.address
        eth_address = eth_address.lower()
        if eth_address.startswith("0x"):
            eth_address = eth_address[2:]
        seed = [ACCOUNT_SEED_VERSION, bytes.fromhex(eth_address)]
        pda, nonce = PublicKey.find_program_address(seed, self._evm_loader)
        return pda, nonce

    def wait_confirmation(self, tx_sig: str, confirmations: tp.Optional[int] = 0) -> bool:
        """Wait transaction status"""

        def get_signature_status():
            resp = self._client.get_signature_statuses([tx_sig])
            result = resp["result"].get("value", [None])[0]
            if result:
                confirmation_status = result["confirmationStatus"]
                confirmation_count = result["confirmations"] or 0
                return (
                    confirmation_status == helpers.SOLCommitmentState.FINALIZED
                    or confirmation_status == helpers.SOLCommitmentState.CONFIRMED
                ) and confirmation_count >= confirmations
            return False

        return try_until(get_signature_status, interval=1, timeout=30)

    def create_eth_account(self) -> "eth_account.account.LocalAccount":
        """Create eth account"""
        account = self._web3.eth.account.create()
        self._faucet.request_neon(account.address, amount=DEFAULT_NEON_AMOUNT)
        return account

    def get_sol_balance(
        self,
        address: tp.Union[str, "eth_account.signers.local.LocalAccount"],
        state: str = helpers.SOLCommitmentState.CONFIRMED,
    ) -> int:
        """Get SOL account balance"""
        if isinstance(address, PublicKey):
            address = str(address)
        elif not isinstance(address, str):
            address = address.address
        return self._client.get_balance(address, commitment=state)["result"]

    def request_sol(
        self,
        address: tp.Union[OperatorAccount, str],
        amount: int = DEFAULT_SOL_AMOUNT,
        state: tp.Optional[str] = helpers.SOLCommitmentState.CONFIRMED,
    ) -> tp.Any:
        """Requests sol to account"""
        if isinstance(address, OperatorAccount):
            address = address.public_key
        elif isinstance(address, PublicKey):
            address = str(address)
        return self._client.request_airdrop(pubkey=address, lamports=amount, commitment=state)["result"]

    def _get_account_data(
        self,
        account: tp.Union[str, PublicKey, OperatorAccount],
        expected_length: int = helpers.ACCOUNT_INFO_LAYOUT.sizeof(),
        state: tp.Optional[str] = helpers.SOLCommitmentState.CONFIRMED,
        timeout: tp.Optional[int] = 60,
    ) -> bytes:
        """Request account info"""
        if isinstance(account, OperatorAccount):
            account = account.public_key
        resp = try_until(
            lambda: self._client.get_account_info(account, commitment=state)["result"].get("value"),
            error_msg=f"Can't get information about {account}\n{self._client.get_account_info(account, commitment=state)} ",
            interval=1,
            timeout=timeout,
        )
        data = base64.b64decode(resp["data"][0])
        if len(data) < expected_length:
            raise Exception(f"Wrong data length for account data {account}")
        return data

    def get_transaction_count(self, account: tp.Union[str, PublicKey, OperatorAccount]) -> int:
        """Get transactions count from account info"""
        info = helpers.AccountInfo.from_bytes(self._get_account_data(account))
        return int.from_bytes(info.trx_count, "little")

    def make_eth_transaction(
        self,
        to_addr: str,
        signer: "eth_account.signers.local.LocalAccount",
        from_solana_user: PublicKey,
        value: int = 0,
        data: bytes = b"",
        nonce: tp.Optional[int] = None,
    ):
        """Create eth transaction"""
        if nonce is None:
            nonce = self.get_transaction_count(from_solana_user)
        tx = {
            "to": to_addr,
            "value": value,
            "gas": 9999999999,
            "gasPrice": 0,
            "nonce": nonce,
            "data": data,
            "chainId": self._credentials["network_id"],
        }
        return self._web3.eth.account.sign_transaction(tx, signer.privateKey)

    def send_transaction(
        self,
        txn,
        acc,
        skip_confirmation: bool = True,
        skip_preflight: bool = False,
        wait_status: tp.Optional[str] = helpers.SOLCommitmentState.PROCESSED,
        blockhash: tp.Optional[Blockhash] = None
    ):
        tx_sig = self._client.send_transaction(
            txn,
            acc,
            recent_blockhash=blockhash,
            opts=TxOpts(
                skip_confirmation=skip_confirmation, skip_preflight=skip_preflight, preflight_commitment=wait_status
            ),
        )["result"]

        return tx_sig

    def make_CreateAccountV02(
            self,
            user_eth_account: "eth_account.account.LocalAccount",
            user_account_bump: int,
            operator: Keypair,
            user_solana_account: PublicKey
    ):
        code = 24
        d = code.to_bytes(1, "little") + bytes.fromhex(user_eth_account.address[2:]) + user_account_bump.to_bytes(1, "little")

        accounts = [
            AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=True),
            AccountMeta(pubkey=user_solana_account, is_signer=False, is_writable=True),
        ]
        return TransactionInstruction(program_id=self._evm_loader, data=d, keys=accounts)

    def make_TransactionExecuteFromInstruction(
        self,
        instruction: bytes,
        operator: Keypair,
        treasury_address: PublicKey,
        treasury_buffer: bytes,
        additional_accounts: tp.List[PublicKey],
    ):
        """Create solana transaction instruction from eth transaction"""
        code = 31
        d = code.to_bytes(1, "little") + treasury_buffer + instruction
        operator_ether_public = eth_keys.PrivateKey(operator.secret_key[:32]).public_key
        operator_ether_solana = self.ether2solana(operator_ether_public.to_address())[0]

        accounts = [
            AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
            AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator_ether_solana, is_signer=False, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=True),
            # Neon EVM account
            AccountMeta(self._evm_loader, is_signer=False, is_writable=False),
        ]
        for acc in additional_accounts:
            accounts.append(
                AccountMeta(acc, is_signer=False, is_writable=True),
            )

        return TransactionInstruction(program_id=self._evm_loader, data=d, keys=accounts)


@dataclass
class TransactionSigner:
    operator: OperatorAccount = None
    treasury_pool: helpers.TreasuryPool = None


@dataclass
class ETHUser:
    eth_account: "eth_account.account.LocalAccount" = None
    sol_account: PublicKey = None
    nonce: int = 0


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
    path = BASE_PATH / environment.parsed_options.credentials
    network = environment.parsed_options.host
    if not (path.exists() and path.is_file()):
        path = BASE_PATH / ENV_FILE
    with open(path, "r") as fp:
        f = json.load(fp)
        environment.credentials = f.get(network, f[DEFAULT_NETWORK])
    environment.host = environment.credentials["solana_url"]


@events.test_start.add_listener
def init_transaction_signers(environment, **kwargs) -> None:
    """Test start event handler - initialize transactions signers"""
    print("Init transaction signers")
    network = environment.parsed_options.host or DEFAULT_NETWORK
    evm_loader_id = environment.credentials["evm_loader"]
    sol_client = SOLClient(environment.credentials, init_session(10))
    environment.operators = gevent.queue.Queue()
    # environment.operators = []

    transaction_signers = [
        TransactionSigner(OperatorAccount(i), helpers.create_treasury_pool_address(network, evm_loader_id))
        for i in range(0, 100)
    ]
    signatures = []
    for op in transaction_signers:
        signatures.append(sol_client.request_sol(op.operator, DEFAULT_SOL_AMOUNT))
        environment.operators.put(op)
    for sig in signatures:
        sol_client.wait_confirmation(sig)
    print("Finish signers")


@events.test_start.add_listener
def precompile_users(environment, **kwargs) -> None:
    print("Precompile users before start")
    users_queue = gevent.queue.Queue()

    def generate_users(count):
        sol_client = SOLClient(environment.credentials, init_session(10))
        operator = environment.operators.get()

        main_user = sol_client.create_eth_account()
        main_user_solana_address = sol_client.ether2solana(main_user.address)[0]
        main_nonce = 0

        for i in range(count):
            user = sol_client._web3.eth.account.create()
            solana_address, bump = sol_client.ether2solana(user.address)

            create_acc = sol_client.make_CreateAccountV02(
                user, bump, operator.operator, solana_address
            )

            eth_transaction = sol_client.make_eth_transaction(
                user.address,
                data=b"",
                signer=main_user,
                from_solana_user=main_user_solana_address,
                value=100000000000,
                nonce=main_nonce,
            )

            send_neon_instr = sol_client.make_TransactionExecuteFromInstruction(
                    eth_transaction.rawTransaction,
                    operator.operator,
                    operator.treasury_pool.account,
                    operator.treasury_pool.buffer,
                    [main_user_solana_address, solana_address],
                )

            tx = helpers.TransactionWithComputeBudget().add(create_acc)
            tx.add(send_neon_instr)
            sol_client.send_transaction(tx, operator.operator, skip_preflight=True)
            main_nonce += 1
            users_queue.put(
                ETHUser(user, solana_address, 0)
            )
        environment.operators.put(operator)

    pool = gevent.get_hub().threadpool
    pool.map(generate_users, [100]*5)
    environment.eth_users = users_queue
    print("Finish prepare users")


class SolanaTransactionTasksSet(TaskSet):
    """Implements solana transaction sender task sets"""

    _last_consumer_id: int = 0
    """Last spawned user id
    """

    tr_sender_id: int = 0
    """Spawned user id
    """

    _setup_class_locker = gevent.threading.Lock()
    _setup_class_done = False

    sol_client: tp.Optional[SOLClient] = None
    """Solana client
    """

    _transaction_signers: tp.Optional[tp.List[TransactionSigner]] = None
    """List operators signed transaction
    """

    _mocked_nonce: int = 0
    _recent_blockhash = ""
    _last_blockhash_time = None

    def get_eth_user(self):
        """Randomly selected recipient of tokens"""
        return self.user.environment.eth_users.get()

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        # setup class once
        with self._setup_class_locker:
            if not SolanaTransactionTasksSet._setup_class_done:
                SolanaTransactionTasksSet._setup_class_done = True
            SolanaTransactionTasksSet._last_consumer_id += 1
            self.tr_sender_id = SolanaTransactionTasksSet._last_consumer_id
        session = init_session(
            self.user.environment.parsed_options.num_users or self.user.environment.runner.target_user_count
        )
        self.sol_client = SOLClient(self.user.environment.credentials, session=session)
        self.log = logging.getLogger("tr-sender[%s]" % self.tr_sender_id)

    @property
    def recent_blockhash(self):
        if self._last_blockhash_time is None or (time.time() - self._last_blockhash_time) > 3:
            self._recent_blockhash = self.sol_client._client.get_recent_blockhash()["result"]["value"]["blockhash"]
            self._last_blockhash_time = time.time()
        return self._recent_blockhash

    @task
    def send_tokens(self) -> None:
        """Create `Neon` transfer solana transaction"""
        token_sender = self.get_eth_user()
        token_receiver = self.get_eth_user()
        operator = self.user.environment.operators.get()

        eth_transaction = self.sol_client.make_eth_transaction(
            token_receiver.eth_account.address,
            data=b"",
            signer=token_sender.eth_account,
            from_solana_user=token_sender.sol_account,
            value=random.randint(1, 10000),
            nonce=token_sender.nonce,
        )
        token_sender.nonce += 1

        trx = helpers.TransactionWithComputeBudget().add(
            self.sol_client.make_TransactionExecuteFromInstruction(
                eth_transaction.rawTransaction,
                operator.operator,
                operator.treasury_pool.account,
                operator.treasury_pool.buffer,
                [token_sender.sol_account, token_receiver.sol_account],
            )
        )

        transaction_receipt = self.sol_client.send_transaction(
            trx,
            operator.operator,
            blockhash=self.recent_blockhash,
            skip_confirmation=True,
            skip_preflight=True
        )
        self.log.info(f"## Token transfer transaction hash: {transaction_receipt}")
        self.user.environment.eth_users.put(token_sender)
        self.user.environment.eth_users.put(token_receiver)
        self.user.environment.operators.put(operator)


class UserTokenSenderTasks(User):
    """Class represents a base task to token send by solana"""

    tasks = {
        SolanaTransactionTasksSet: 1,
    }
