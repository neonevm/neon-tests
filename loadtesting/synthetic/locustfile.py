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
from hashlib import sha256

import requests
import web3
from eth_keys import keys as eth_keys
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.api import Client as SolanaClient
from solana.rpc.providers import http
from solana.rpc.types import TxOpts
from solana.system_program import SYS_PROGRAM_ID
from solana.transaction import AccountMeta, Transaction, TransactionInstruction

from ui.libs import try_until
from utils import faucet
from . import utils

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


DEFAULT_UNITS = 500 * 1000
DEFAULT_HEAP_FRAME = 256 * 1024
DEFAULT_ADDITIONAL_FEE = 0
COMPUTE_BUDGET_ID: PublicKey = PublicKey("ComputeBudget111111111111111111111111111111")


class ComputeBudget:
    @staticmethod
    def request_units(units, additional_fee):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[],
            data=bytes.fromhex("00") + units.to_bytes(4, "little") + additional_fee.to_bytes(4, "little")
        )

    @staticmethod
    def request_heap_frame(heap_frame):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[],
            data=bytes.fromhex("01") + heap_frame.to_bytes(4, "little")
        )


class TransactionWithComputeBudget(Transaction):
    def __init__(self,
                 units=DEFAULT_UNITS,
                 additional_fee=DEFAULT_ADDITIONAL_FEE,
                 heap_frame=DEFAULT_HEAP_FRAME,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        # if units:
        #     self.instructions.append(ComputeBudget.request_units(units, additional_fee))
        if heap_frame:
            self.instructions.append(ComputeBudget.request_heap_frame(heap_frame))


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
            f"--commitment={utils.SOLCommitmentState.PROCESSED} "
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

    def __init__(self, credentials: tp.Dict = None, session: tp.Optional[tp.Any] = None, timeout: float = 10) -> None:
        self._credentials = credentials or load_credentials()
        self._web3 = web3.Web3(web3.HTTPProvider(""))
        self._session = session or init_session(DEFAULT_USER_NUM)
        self._faucet = faucet.Faucet(self._credentials["faucet_url"], self._session)
        self._evm_loader = EvmLoader(self._credentials["evm_loader"], self._credentials["solana_url"])
        self._client = SolanaClient()
        self._client._provider = ExtendedHTTPProvider(self._credentials["solana_url"], timeout=timeout)

    @property
    def evm_loader_id(self) -> str:
        return self._evm_loader.loader_id

    def wait_confirmation(self, tx_sig: str, confirmations: tp.Optional[int] = 0) -> bool:
        """"""

        def get_signature_status():
            resp = self._client.get_signature_statuses([tx_sig])
            result = resp["result"].get("value", [None])[0]
            if result:
                confirmation_status = result["confirmationStatus"]
                confirmation_count = result["confirmations"] or 0
                return (
                    confirmation_status == utils.SOLCommitmentState.FINALIZED
                    or confirmation_status == utils.SOLCommitmentState.CONFIRMED
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
        state: str = utils.SOLCommitmentState.CONFIRMED,
    ) -> int:
        if isinstance(address, PublicKey):
            address = str(address)
        elif not isinstance(address, str):
            address = address.address
        return self._client.get_balance(address, commitment=state)["result"]

    def request_sol(
        self,
        address: tp.Union[OperatorAccount, str],
        amount: int = DEFAULT_SOL_AMOUNT,
        state: tp.Optional[str] = utils.SOLCommitmentState.CONFIRMED,
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
        expected_length: int = utils.ACCOUNT_INFO_LAYOUT.sizeof(),
        state: tp.Optional[str] = utils.SOLCommitmentState.CONFIRMED,
        timeout: tp.Optional[int] = 60,
    ) -> bytes:
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
        info = utils.AccountInfo.from_bytes(self._get_account_data(account))
        return int.from_bytes(info.trx_count, "little")

    def make_eth_transaction(
        self, to_addr: str, signer: OperatorAccount, from_solana_user: PublicKey, value: int = 0, data: bytes = b"",
    ):
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
        return self._web3.eth.account.sign_transaction(tx, signer.secret_key[:32])

    def create_storage_account(
        self, signer: OperatorAccount, seed: bytes = None, size: int = None, fund: int = None
    ) -> PublicKey:
        if size is None:
            size = 128 * 1024
        if fund is None:
            fund = 10 ** 9
        if seed is None:
            seed = str(random.randrange(1000000))
        storage = PublicKey(
            sha256(bytes(signer.public_key) + bytes(seed, "utf8") + bytes(PublicKey(self.evm_loader_id))).digest()
        )

        if self.get_sol_balance(storage).get("value") == 0:
            txn = Transaction().add(
                utils.create_account_with_seed(
                    signer.public_key, signer.public_key, seed, fund, size, self.evm_loader_id
                )
            )
            self.send_transaction(txn, signer)
        return storage

    def send_transaction(
        self,
        txn,
        acc,
        skip_confirmation: bool = True,
        skip_preflight: bool = False,
        wait_status: tp.Optional[str] = utils.SOLCommitmentState.CONFIRMED,
    ):
        tx_sig = self._client.send_transaction(
            txn,
            acc,
            opts=TxOpts(
                skip_confirmation=skip_confirmation, skip_preflight=skip_preflight, preflight_commitment=wait_status
            ),
        )["result"]
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
        code = 31
        d = code.to_bytes(1, "little") + treasury_buffer + instruction
        operator_ether = eth_keys.PrivateKey(operator.secret_key[:32]).public_key.to_canonical_address()

        accounts = [
            AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
            AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self._evm_loader.ether2program(operator_ether)[0], is_signer=False, is_writable=True),
            # AccountMeta(pubkey=PublicKey("7TUndyBSqVx4zeXVPMh2ChFNDCZBJpq7ADiDEWzqQUCw"), is_signer=False, is_writable=True),
            AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=True),
            # Neon EVM account
            AccountMeta(self.evm_loader_id, is_signer=False, is_writable=False),
        ]
        for acc in additional_accounts:
            accounts.append(
                AccountMeta(acc, is_signer=False, is_writable=True),
            )

        return TransactionInstruction(program_id=self.evm_loader_id, data=d, keys=accounts)


sol_client = SOLClient()


def create_transaction():
    print("# # Create transaction signer `operator`")
    # operator = OperatorAccount(random.choice(range(2, 31)))
    operator = OperatorAccount(2)
    print("# # request SOL to transaction signer")
    tx_sig = sol_client.request_sol(operator, 1000)
    sol_client.wait_confirmation(tx_sig)
    print("# # Create solana program from `operator` eth address")
    operator_sol_program = sol_client.create_solana_program(operator.eth_address)[0]
    print(f"Operator sol address {operator_sol_program} / public {operator.public_key}")
    print("# # Create sender eth account")
    from_eth_account_address = sol_client.create_eth_account().address
    print(f"From ethereum address: {from_eth_account_address}")
    print("# # Create solana program from `sender` eth address")
    from_sol_account_address = sol_client.create_solana_program(from_eth_account_address)[0]
    print(f"Solana from addr: {from_sol_account_address}")
    print("# # Create one more account to receive neons")
    to_eth_account_address = sol_client.create_eth_account().address
    print(f"From ethereum address: {to_eth_account_address}")
    to_sol_account_address = sol_client.create_solana_program(to_eth_account_address)[0]
    print(f"Solana to addr: {to_sol_account_address}")
    print("# # create eth transaction")
    eth_transaction = sol_client.make_eth_transaction(
        to_eth_account_address,
        data=b"",
        signer=operator,
        from_solana_user=from_sol_account_address,
    )
    print("# # Create storage account")
    treasury_pool = utils.create_treasury_pool_address(DEFAULT_NETWORK, sol_client.evm_loader_id)
    print("# # Create transaction")

    print(f"ETH transaction {eth_transaction.hash}")

    trx = TransactionWithComputeBudget().add(
        sol_client.make_TransactionExecuteFromInstruction(
            eth_transaction.rawTransaction,
            operator,
            treasury_pool.account,
            treasury_pool.buffer,
            [PublicKey(from_sol_account_address), PublicKey(to_sol_account_address)],
        )
    )
    print("# # Send transaction")
    receipt = sol_client.send_transaction(trx, operator, skip_preflight=True)
    return receipt
