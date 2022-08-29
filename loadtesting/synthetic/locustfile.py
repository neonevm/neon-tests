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
import random
import subprocess
import typing as tp
from dataclasses import dataclass

import requests
import web3
from solana.account import Account as SOLAccount
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc import commitment
from solana.rpc.api import Client as SolanaClient

# from solana.transaction import AccountMeta, TransactionInstruction  # , Transaction
from eth_keys import keys as eth_keys
from solana.rpc.providers import http
from construct import Bytes, Int8ul, Struct

from ui.libs import try_until
from utils import faucet

LOG = logging.getLogger("sol-client")

DEFAULT_NETWORK = os.environ.get("NETWORK", "night-stand")
"""Default test environment name
"""

ENV_FILE = "envs.json"
""" Default environment credentials storage 
"""

DEFAULT_USER_NUM = 10
"""
"""

DEFAULT_NEON_AMOUNT = 100
"""
"""
DEFAULT_SOL_AMOUNT = 1000000 * 10 ** 9

CWD = pathlib.Path(__file__).parent
"""Current working directory"""

BASE_PATH = CWD.parent.parent
"""Project root directory"""

SYS_INSTRUCT_ADDRESS = "Sysvar1nstructions1111111111111111111111111"
"""
"""

ACCOUNT_INFO_LAYOUT = Struct(
    "type" / Int8ul,
    "ether" / Bytes(20),
    "nonce" / Int8ul,
    "trx_count" / Bytes(8),
    "balance" / Bytes(32),
    "code_account" / Bytes(32),
    "is_rw_blocked" / Int8ul,
    "ro_blocked_cnt" / Int8ul,
)


@dataclass
class AccountInfo:
    ether: eth_keys.PublicKey
    code_account: PublicKey
    trx_count: int

    @staticmethod
    def from_bytes(data: bytes):
        cont = ACCOUNT_INFO_LAYOUT.parse(data)
        return AccountInfo(cont.ether, PublicKey(cont.code_account), cont.trx_count)


@dataclass
class SOLCommitmentState:
    """Bank states to solana query"""

    CONFIRMED: str = commitment.Confirmed
    FINALIZED: str = commitment.Finalized
    PROCESSED: str = commitment.Processed


def init_session(size: int) -> requests.Session:
    """init request session with extended connection pool size"""
    adapter = requests.adapters.HTTPAdapter(pool_connections=size, pool_maxsize=size, pool_block=True)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def load_credentials(*args, **kwargs) -> tp.Dict:
    """Test start event handler"""
    path = BASE_PATH / ENV_FILE
    with open(path, "r") as fp:
        f = json.load(fp)
        return f[DEFAULT_NETWORK]


def handle_failed_requests(func: tp.Callable) -> tp.Callable:
    """Extends solana client functional"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> tp.Any:
        resp = func(self, *args, **kwargs)
        if resp.get("error"):
            raise AssertionError(
                f"Request {func.__name__} is failed: {resp['error']['code']} - {resp['error']['message']}"
            )
        return resp["result"]

    return wrapper


class ExtendedHTTPProvider(http.HTTPProvider):
    @handle_failed_requests
    def make_request(self, *args, **kwargs) -> tp.Dict:
        print(f"{30*'_'} Make extended request")
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
            f"--commitment={SOLCommitmentState.PROCESSED} "
            f"--url {self._solana_url} "
            f"--evm_loader {self._loader_id} "
            f"{comand.replace('_','-')} {''.join(map(str, args))}"
        )
        try:
            return subprocess.check_output(cmd, shell=True, universal_newlines=True)
        except subprocess.CalledProcessError as err:
            print(f"ERR: neon-cli error {err}")
            raise


class OperatorAccount(SOLAccount):
    """Implements operator Account"""

    def __init__(self, key_id: tp.Optional[int] = None) -> None:
        self._path = CWD / f"operator-keypairs/id{key_id or ''}.json"
        if not self._path.exists():
            raise FileExistsError(f"Operator key `{self._path}` not exists")
        with open(self._path) as fd:
            key = json.load(fd)[:32]
        super(OperatorAccount, self).__init__(key)

    def get_path(self) -> str:
        """Return operator key storage path"""
        return self._path.as_posix()


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


class SOLClient(SolanaClient):
    """"""

    def __init__(self, credentials: tp.Dict = None, session: tp.Optional[tp.Any] = None, timeout: float = 10) -> None:
        credentials = credentials or load_credentials()
        self._web3 = web3.Web3(web3.HTTPProvider(""))
        self._session = session or init_session(DEFAULT_USER_NUM)
        self._faucet = faucet.Faucet(credentials["faucet_url"], self._session)
        self._evm_loader = EvmLoader(credentials["evm_loader"], credentials["solana_url"])
        super(SOLClient, self).__init__()
        self._provider = ExtendedHTTPProvider(credentials["solana_url"], timeout=timeout)

    def wait_confirmation(self, tx_sig: str, confirmations: tp.Optional[int] = 0) -> bool:
        """"""

        def get_signature_status():
            resp = self.get_signature_statuses([tx_sig])
            result = resp.get("value", [None])[0]
            if result:
                confirmation_status = result["confirmationStatus"]
                confirmation_count = result["confirmations"] or 0
                return (
                    confirmation_status == SOLCommitmentState.FINALIZED
                    or confirmation_status == SOLCommitmentState.CONFIRMED
                ) and confirmation_count >= confirmations
            return False

        return try_until(get_signature_status, interval=1, timeout=30)

    def create_eth_account(self) -> "eth_account.local.LocalAccount":
        account = self._web3.eth.account.create()
        self._faucet.request_neon(account.address, amount=DEFAULT_NEON_AMOUNT)
        return account

    def create_solana_program(self, account: "eth_account.local.LocalAccount") -> tp.Tuple[tp.Any]:
        return self._evm_loader.ether2program(account)

    def get_sol_balance(
        self,
        address: tp.Union[str, "eth_account.signers.local.LocalAccount"],
        state: str = SOLCommitmentState.CONFIRMED,
    ) -> int:
        if isinstance(address, PublicKey):
            address = str(address)
        elif not isinstance(address, str):
            address = address.address
        return self.get_balance(address, commitment=state)

    def request_sol(
        self,
        address: tp.Union[OperatorAccount, str],
        amount: int = DEFAULT_SOL_AMOUNT,
        state: str = SOLCommitmentState.CONFIRMED,
    ) -> tp.Any:
        """Requests sol to account"""
        if isinstance(address, OperatorAccount):
            address = address.public_key()
        elif isinstance(address, PublicKey):
            address = str(address)
        return self.request_airdrop(pubkey=address, lamports=amount, commitment=state)

    def get_account_data(
        self,
        account: tp.Union[str, PublicKey, Keypair, OperatorAccount],
        expected_length: int = ACCOUNT_INFO_LAYOUT.sizeof(),
    ) -> bytes:
        if isinstance(account, Keypair):
            account = account.public_key
        elif isinstance(account, OperatorAccount):
            account = account.public_key()
        resp = self.get_account_info(account, commitment=SOLCommitmentState.CONFIRMED).get("value")
        if not resp:
            raise Exception(f"Can't get information about {account}")
        data = base64.b64decode(resp["data"][0])
        if len(data) < expected_length:
            raise Exception(f"Wrong data length for account data {account}")
        return data

    def get_transaction_count(self, account: tp.Union[str, PublicKey, OperatorAccount]) -> int:
        if isinstance(account, Keypair):
            account = account.public_key
        elif isinstance(account, OperatorAccount):
            account = account.public_key()
        info = AccountInfo.from_bytes(self.get_account_data(account))
        return int.from_bytes(info.trx_count, "little")

    """
    def make_PartialCallOrContinueFromRawEthereumTX(
        self,
        instruction: bytes,
        operator: Keypair,
        evm_loader: "EvmLoader",
        storage_address: PublicKey,
        treasury_address: PublicKey,
        treasury_buffer: bytes,
        step_count: int,
        additional_accounts: tp.List[PublicKey],
    ):
        code = 13
        d = code.to_bytes(1, "little") + treasury_buffer + step_count.to_bytes(8, byteorder="little") + instruction
        operator_ether = eth_keys.PrivateKey(operator.secret_key[:32]).public_key.to_canonical_address()

        accounts = [
            AccountMeta(pubkey=storage_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=SYS_INSTRUCT_ADDRESS, is_signer=False, is_writable=True),
            AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
            AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=evm_loader.ether2program(operator_ether)[0], is_signer=False, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=True),
            # Neon EVM account
            AccountMeta(EVM_LOADER, is_signer=False, is_writable=False),
        ]
        for acc in additional_accounts:
            accounts.append(
                AccountMeta(acc, is_signer=False, is_writable=True),
            )

        return TransactionInstruction(program_id=EVM_LOADER, data=d, keys=accounts)

    def make_eth_transaction(to_addr: str, data: bytes, signer: Keypair, from_solana_user: PublicKey,
                             user_eth_address: bytes):
        nonce = get_transaction_count(solana_client, from_solana_user)
        tx = {'to': to_addr, 'value': 0, 'gas': 9999999999, 'gasPrice': 0,
              'nonce': nonce, 'data': data, 'chainId': 111}
        (from_addr, sign, msg) = make_instruction_data_from_tx(tx, signer.secret_key[:32])
        assert from_addr == user_eth_address, (from_addr, user_eth_address)
        return from_addr, sign, msg, nonce
    """


sol_client = SOLClient()


def create_transaction():
    operator = OperatorAccount(random.choice(range(2, 31)))
    tx_sig = sol_client.request_airdrop(operator, 1000)
    sol_client.wait_confirmation(tx_sig)
    eth_account_address = sol_client.create_eth_account().address
    sol_account_address = sol_client.create_solana_program(eth_account_address)[0]
    sol_client.request_airdrop(sol_account_address, 1000)
    sol_client.wait_confirmation(tx_sig)
