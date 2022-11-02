import base64
import json
import time
import os
import pathlib
import random
import typing as tp
from dataclasses import dataclass

import gevent
import gevent.queue

import web3
import eth_account
from eth_keys import keys as eth_keys
from locust import TaskSet, User, events, task
from locust.contrib.fasthttp import FastHttpSession
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


DEFAULT_NETWORK = os.environ.get("NETWORK", "night-stand")
ENV_FILE = "envs.json"
CWD = pathlib.Path(__file__).parent
BASE_PATH = CWD.parent.parent

OPERATORS_COUNT = int(os.environ.get("OPERATORS_COUNT", "300"))
OPERATORS_OFFSET = int(os.environ.get("OPERATORS_OFFSET", "0"))

ACCOUNT_SEED_VERSION = b'\2'
ACCOUNT_ETH_BASE = int("0xc26286eebe70b838545855325d45b123149c3ca4a50e98b1fe7c7887e3327aa8", 16)

PREPARED_USERS_OFFSET = int(os.environ.get("USERS_OFFSET", "0"))
PREPARED_USERS_COUNT = int(os.environ.get("USERS_COUNT", "1000"))


class FastSolanaClient(http.HTTPProvider):
    def __init__(self, *args, **kwargs):
        env = kwargs.pop("environment")
        user = kwargs.pop("user")
        base_url = kwargs.pop("base_url")
        super().__init__(*args, **kwargs)
        self.fast_http = FastHttpSession(environment=env, user=user, base_url=base_url)

    def make_request(self, method, *params):
        request_kwargs = self._before_request(method=method, params=params, is_async=False)
        raw_response = self.fast_http.post("/", data=request_kwargs["data"], headers=request_kwargs["headers"])
        return self._after_request(raw_response=raw_response, method=method)


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
    def __init__(self, credentials: tp.Dict, **kwargs) -> None:
        self._web3 = web3.Web3()
        self._evm_loader = PublicKey(credentials["evm_loader"])
        self._client = SolanaClient()
        self._client._provider = FastSolanaClient(environment=kwargs.get("environment"),
                                                  user=kwargs.get("user"),
                                                  base_url=credentials["solana_url"])
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
        # print(f"SOL address: {from_solana_user}")
        if nonce is None or nonce == 0:
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
        return self._web3.eth.account.sign_transaction(tx, signer.privateKey), nonce

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
    environment.operators = gevent.queue.Queue()

    transaction_signers = [
        TransactionSigner(OperatorAccount(i), helpers.create_treasury_pool_address(network, evm_loader_id, i))
        for i in range(OPERATORS_OFFSET, OPERATORS_COUNT + OPERATORS_OFFSET)
    ]

    for op in transaction_signers:
        environment.operators.put(op)
    print("Finish signers")


@events.test_start.add_listener
def precompile_users(environment, **kwargs) -> None:
    print("Precompile users before start")
    users_queue = gevent.queue.Queue()
    web = web3.Web3()
    sol_client = SOLClient(environment.credentials, environment=environment, user=None)

    for i in range(0, PREPARED_USERS_COUNT+1):
        user = web.eth.account.from_key(ACCOUNT_ETH_BASE + PREPARED_USERS_OFFSET + i)
        solana_address, bump = sol_client.ether2solana(user.address)
        users_queue.put(ETHUser(user, solana_address, 0))

    environment.eth_users = users_queue
    print("Finish prepare users")


class SolanaTransactionTasksSet(TaskSet):
    """Implements solana transaction sender task sets"""
    sol_client: tp.Optional[SOLClient] = None
    _recent_blockhash = ""
    _last_blockhash_time = None

    def get_eth_user(self):
        """Randomly selected recipient of tokens"""
        return self.user.environment.eth_users.get()

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        self.sol_client = SOLClient(self.user.environment.credentials, environment=self.user.environment, user=self.user)

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
        eth_transaction, new_nonce = self.sol_client.make_eth_transaction(
            token_receiver.eth_account.address,
            data=b"",
            signer=token_sender.eth_account,
            from_solana_user=token_sender.sol_account,
            value=random.randint(1, 10000),
            nonce=token_sender.nonce,
        )
        token_sender.nonce = new_nonce + 1

        trx = helpers.TransactionWithComputeBudget().add(
            self.sol_client.make_TransactionExecuteFromInstruction(
                eth_transaction.rawTransaction,
                operator.operator,
                operator.treasury_pool.account,
                operator.treasury_pool.buffer,
                [token_sender.sol_account, token_receiver.sol_account],
            )
        )

        req_event = {
            "request_type": "solana",
            "name": "send_neon",
            "start_time": time.time(),
            "response_length": 0,
            "context": {},
            "response": None,
            "exception": None
        }
        start_perf_counter = time.perf_counter()
        transaction_receipt = self.sol_client.send_transaction(
            trx,
            operator.operator,
            blockhash=self.recent_blockhash,
            skip_confirmation=True,
            skip_preflight=True
        )
        req_event["response_time"] = (time.perf_counter() - start_perf_counter) * 1000
        self.user.environment.events.request.fire(**req_event)
        self.user.environment.eth_users.put(token_receiver)
        self.user.environment.eth_users.put(token_sender)
        self.user.environment.operators.put(operator)


class UserTokenSenderTasks(User):
    """Class represents a base task to token send by solana"""

    tasks = {
        SolanaTransactionTasksSet: 1,
    }
