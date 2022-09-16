# coding: utf-8
"""
Created on 2022-08-18
@author: Eugeny Kurkovich
"""
import base64
import functools
import json
import logging
import os
import pathlib
import subprocess
import typing as tp
from dataclasses import dataclass

import gevent
import requests
import web3
from eth_keys import keys as eth_keys
from locust import TaskSet, User, events, tag, task, between
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.api import Client as SolanaClient
from solana.rpc.providers import http
from solana.rpc.types import TxOpts
from solana.system_program import SYS_PROGRAM_ID
from solana.transaction import AccountMeta, TransactionInstruction

from ui.libs import try_until
from utils import faucet
from loadtesting.synthetic import helpers

LOG = logging.getLogger("sol-client")

DEFAULT_NETWORK = os.environ.get("NETWORK", "night-stand")
"""Default test environment name
"""

ENV_FILE = "envs.json"
""" Default environment credentials storage 
"""

DEFAULT_USER_NUM = 10
"""Default peak number of concurrent Locust users.
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
"""
"""

DEFAULT_OPERATOR_KEY_PAIR_ID = 2


def init_session(size: int) -> requests.Session:
    """init request session with extended connection pool size"""
    adapter = requests.adapters.HTTPAdapter(pool_connections=size, pool_maxsize=size, pool_block=True)
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


class NeonClient:
    """Implements neon client functionality"""

    def __init__(self, evm_loader_id: str, solana_url: str, verbose_flags: tp.Optional[str] = "") -> None:
        self._verbose_flags = verbose_flags
        self._loader_id = evm_loader_id
        self._solana_url = solana_url

    def __getattr__(self, item):

        global command
        command = item

        def wrapper(*args, **kwargs):
            return self._run_cli(command, *args, **kwargs)

        return wrapper

    def _run_cli(self, comand, *args):
        cmd = (
            f"neon-cli {self._verbose_flags} "
            f"-vvv "
            f"--commitment={helpers.SOLCommitmentState.PROCESSED} "
            f"--url {self._solana_url} "
            f"--evm_loader {self._loader_id} "
            f"{comand.replace('_','-')} {''.join(map(str, args))}"
        )
        try:
            return subprocess.check_output(cmd, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as err:
            print(f"ERR: neon-cli error {err}")
            raise


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
        return eth_keys.PrivateKey(self.secret_key[:32]).public_key.to_canonical_address()


class EvmLoader:
    """Implements base functionality of the evm loader"""

    def __init__(self, loader_id: str, solana_url: str, account: tp.Optional["OperatorAccount"] = None) -> None:
        self.loader_id = loader_id
        self.account = account
        self._neon_client = NeonClient(self.loader_id, solana_url)

    def ether2program(self, ether):
        """Create solana program from eth account, return program address and nonce"""

        if hasattr(ether, "address"):
            ether = ether.address
        elif not isinstance(ether, str):
            ether = ether.hex()
        if ether.startswith("0x"):
            ether = ether[2:]
        cli_output = self._neon_client.create_program_address(ether)
        items = cli_output.rstrip().split(" ")
        return items[0], int(items[1])


class SOLClient:
    """"""

    def __init__(self, credentials: tp.Dict, session: tp.Optional[requests.Session], timeout: float = 10) -> None:
        self._web3 = web3.Web3(web3.HTTPProvider(""))
        self._faucet = faucet.Faucet(credentials["faucet_url"], session)
        self._evm_loader = EvmLoader(credentials["evm_loader"], credentials["solana_url"])
        self._client = SolanaClient()
        self._client._provider = ExtendedHTTPProvider(credentials["solana_url"], timeout=timeout)
        self._credentials = credentials

    def __getattr__(self, item) -> tp.Any:
        return getattr(self._client, item)

    @property
    def evm_loader_id(self) -> str:
        return self._evm_loader.loader_id

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

    def create_eth_account(self) -> "eth_account.local.LocalAccount":
        """Create eth account"""
        account = self._web3.eth.account.create()
        self._faucet.request_neon(account.address, amount=DEFAULT_NEON_AMOUNT)
        return account

    def create_solana_program(self, account: "eth_account.local.LocalAccount") -> tp.Tuple[tp.Any]:
        return self._evm_loader.ether2program(account)

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
        signer: "eth_account.local.LocalAccount",
        from_solana_user: PublicKey,
        value: int = 0,
        data: bytes = b"",
    ):
        """Create eth transaction"""
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
        wait_status: tp.Optional[str] = helpers.SOLCommitmentState.CONFIRMED,
        wait_confirmed_transaction: bool = False,
    ):
        tx_sig = self._client.send_transaction(
            txn,
            acc,
            opts=TxOpts(
                skip_confirmation=skip_confirmation, skip_preflight=skip_preflight, preflight_commitment=wait_status
            ),
        )["result"]
        trx = None
        if wait_confirmed_transaction:
            self.wait_confirmation(tx_sig)
            trx = try_until(
                lambda: self._client.get_confirmed_transaction(tx_sig)["result"],
                interval=10,
                timeout=60,
                error_msg=f"Can't get confirmed transaction {tx_sig}",
            )
        return tx_sig, trx

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
        operator_ether = eth_keys.PrivateKey(operator.secret_key[:32]).public_key.to_canonical_address()
        print(f"Operator ether {operator_ether.hex()}")
        operator_ether_solana = self._evm_loader.ether2program(operator_ether)[0]
        print(f"Operator ether solana {operator_ether_solana}")

        accounts = [
            AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
            AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator_ether_solana, is_signer=False, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=True),
            # Neon EVM account
            AccountMeta(self.evm_loader_id, is_signer=False, is_writable=False),
        ]
        for acc in additional_accounts:
            accounts.append(
                AccountMeta(acc, is_signer=False, is_writable=True),
            )

        return TransactionInstruction(program_id=self.evm_loader_id, data=d, keys=accounts)


@dataclass
class TransactionSigner:
    operator: OperatorAccount = None
    treasury_pool: helpers.TreasuryPool = None


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


@events.test_start.add_listener
def init_transaction_signers(environment, **kwargs) -> None:
    """Test start event handler - initialize transactions signers"""
    network = environment.parsed_options.host or DEFAULT_NETWORK
    evm_loader_id = environment.credentials["evm_loader"]
    environment.transaction_signers = [
        TransactionSigner(OperatorAccount(i), helpers.create_treasury_pool_address(network, evm_loader_id))
        for i in range(1, 31)
    ]


class SolanaTransactionTasksSet(TaskSet):
    """Implements solana transaction sender task sets"""

    _last_consumer_id: int = 0
    """Last spawned user id
    """

    tr_sender_id: int = 0
    """Spawned user id
    """

    tr_signer: tp.Optional[TransactionSigner] = None
    """Transaction signer
    """

    _setup_class_locker = gevent.threading.Lock()
    _setup_class_done = False

    sol_client: tp.Optional[SOLClient] = None
    """Solana client
    """

    _transaction_signers: tp.Optional[tp.List[TransactionSigner]] = None
    """List operators signed transaction
    """

    token_sender: tp.Optional["eth_account.local.LocalAccount"] = None
    """
    """

    token_sender_sol_account: tp.Optional[tp.Any] = None
    """
    """

    token_receiver: tp.Optional["eth_account.local.LocalAccount"] = None
    """
    """

    token_receiver_sol_account: tp.Optional[tp.Any] = None
    """
    """

    def prepare_accounts(self) -> None:
        """Prepare data requirements"""
        operator = self.tr_signer.operator
        self.log.info(f"# # request SOL to `operator` {operator.eth_address.hex()}")
        sig = self.sol_client.request_sol(operator, DEFAULT_SOL_AMOUNT)
        self.sol_client.wait_confirmation(sig)
        self.log.info(f"# # create solana program from `operator` eth address: {operator.eth_address.hex()}")
        sol_program = self.sol_client.create_solana_program(operator.eth_address)[0]
        self.log.info(f"sol program from `operator` address {sol_program}")
        self.log.info(f"# # create token sender eth account")
        self.token_sender = self.sol_client.create_eth_account()
        self.log.info(f"# # create solana program from `token sender` eth address: {self.token_sender.address}")
        self.token_sender_sol_account = self.sol_client.create_solana_program(self.token_sender.address)[0]
        self.log.info(f"# # `token sender` solana  address: {self.token_sender_sol_account}")
        self.log.info("# # create one more account to receive `NEON` tokens")
        self.token_receiver = self.sol_client.create_eth_account()
        self.log.info(f"# # create solana program from ~token receiver` eth address: {self.token_receiver.address}")
        self.token_receiver_sol_account = self.sol_client.create_solana_program(self.token_receiver)[0]
        self.log.info(f"Token `receiver` solana address: {self.token_receiver_sol_account}")

    def on_start(self) -> None:
        """on_start is called when a Locust start before any task is scheduled"""
        # setup class once
        with self._setup_class_locker:
            if not SolanaTransactionTasksSet._setup_class_done:
                SolanaTransactionTasksSet._transaction_signers = self.user.environment.transaction_signers
                SolanaTransactionTasksSet._setup_class_done = True
            SolanaTransactionTasksSet._last_consumer_id += 1
            self.tr_sender_id = SolanaTransactionTasksSet._last_consumer_id
            self.tr_signer = SolanaTransactionTasksSet._transaction_signers.pop(0)
            SolanaTransactionTasksSet._transaction_signers.append(self.tr_signer)
        session = init_session(
            self.user.environment.parsed_options.num_users or self.user.environment.runner.target_user_count
        )
        self.sol_client = SOLClient(self.user.environment.credentials, session)
        self.log = logging.getLogger("tr-sender[%s]" % self.tr_sender_id)
        self.prepare_accounts()

    @task
    def send_tokens(self) -> None:
        """Create `Neon` transfer solana transaction"""

        self.log.info("# # create eth transaction")
        eth_transaction = self.sol_client.make_eth_transaction(
            self.token_receiver.address,
            data=b"",
            signer=self.token_sender,
            from_solana_user=self.token_sender_sol_account,
            value=1,
        )
        self.log.info(f"# # ETH transaction {eth_transaction.hash.hex()}")
        self.log.info("# # create token transfer transaction instruction")
        trx = helpers.TransactionWithComputeBudget().add(
            self.sol_client.make_TransactionExecuteFromInstruction(
                eth_transaction.rawTransaction,
                self.tr_signer.operator,
                self.tr_signer.treasury_pool.account,
                self.tr_signer.treasury_pool.buffer,
                [PublicKey(self.token_sender_sol_account), PublicKey(self.token_receiver_sol_account)],
            )
        )
        self.log.info("# # Send transaction")
        transaction_receipt = self.sol_client.send_transaction(
            trx, self.tr_signer.operator, skip_preflight=False, wait_status=helpers.SOLCommitmentState.PROCESSED
        )
        self.log.info(f"# # token transfer transaction hash: {transaction_receipt[0]}")


class UserTokenSenderTasks(User):
    """Class represents a base task to token send by solana"""

    tasks = {
        SolanaTransactionTasksSet: 1,
    }
