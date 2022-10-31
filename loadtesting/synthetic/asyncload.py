import os
import typing as tp
import base64
import json
import asyncio
import random
import pathlib
from dataclasses import dataclass

import web3
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.async_api import AsyncClient
import eth_account
from eth_keys import keys as eth_keys
import helpers
from solana.transaction import AccountMeta, TransactionInstruction
from solana.system_program import SYS_PROGRAM_ID
from solana.rpc.types import TxOpts


SOLANA_URL = "http://proxy.night.stand.neontest.xyz/node-solana"
EVM_LOADER_ID = "53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io"
ACCOUNT_SEED_VERSION = b'\2'
ACCOUNT_ETH_BASE = int("0xc26286eebe70b838545855325d45b123149c3ca4a50e98b1fe7c7887e3327aa8", 16)

OPERATORS_COUNT = int(os.environ.get("OPERATORS_COUNT", "1000"))
OPERATORS_OFFSET = int(os.environ.get("OPERATORS_OFFSET", "0"))

PREPARED_USERS_OFFSET = int(os.environ.get("USERS_OFFSET", "0"))
PREPARED_USERS_COUNT = int(os.environ.get("USERS_COUNT", "10000"))

USERS_QUEUE = asyncio.Queue()
OPERATORS_QUEUE = asyncio.Queue()

w3 = web3.Web3()


class OperatorAccount(Keypair):
    """Implements operator Account"""

    def __init__(self, key_id: tp.Optional[int] = "") -> None:
        self._path = pathlib.Path(__file__).parent / f"operator-keypairs/id{key_id}.json"
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


@dataclass
class TransactionSigner:
    operator: OperatorAccount = None
    treasury_pool: helpers.TreasuryPool = None


@dataclass
class ETHUser:
    eth_account: "eth_account.account.LocalAccount" = None
    sol_account: PublicKey = None
    nonce: int = 0


def ether2solana(eth_address: tp.Union[str, "eth_account.account.LocalAccount"]) -> tp.Tuple[PublicKey, int]:
    if isinstance(eth_address, (eth_account.account.LocalAccount, eth_account.signers.local.LocalAccount)):
        eth_address = eth_address.address
    eth_address = eth_address.lower()
    if eth_address.startswith("0x"):
        eth_address = eth_address[2:]
    seed = [ACCOUNT_SEED_VERSION, bytes.fromhex(eth_address)]
    pda, nonce = PublicKey.find_program_address(seed, PublicKey(EVM_LOADER_ID))
    return pda, nonce


def make_eth_transaction(
    to_addr: str,
    signer: "eth_account.signers.local.LocalAccount",
    value: int = 0,
    data: bytes = b"",
    nonce: tp.Optional[int] = None,
):
    """Create eth transaction"""
    tx = {
        "to": to_addr,
        "value": value,
        "gas": 9999999999,
        "gasPrice": 0,
        "nonce": nonce,
        "data": data,
        "chainId": 111,
    }
    return w3.eth.account.sign_transaction(tx, signer.privateKey)


def make_TransactionExecuteFromInstruction(
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
    operator_ether_solana = ether2solana(operator_ether_public.to_address())[0]
    accounts = [
        AccountMeta(pubkey=operator.public_key, is_signer=True, is_writable=True),
        AccountMeta(pubkey=treasury_address, is_signer=False, is_writable=True),
        AccountMeta(pubkey=operator_ether_solana, is_signer=False, is_writable=True),
        AccountMeta(SYS_PROGRAM_ID, is_signer=False, is_writable=True),
        # Neon EVM account
        AccountMeta(PublicKey(EVM_LOADER_ID), is_signer=False, is_writable=False),
    ]
    for acc in additional_accounts:
        accounts.append(
            AccountMeta(acc, is_signer=False, is_writable=True),
        )

    return TransactionInstruction(program_id=PublicKey(EVM_LOADER_ID), data=d, keys=accounts)


async def get_account_data(
        sol_client,
    account: tp.Union[str, PublicKey, OperatorAccount],
    expected_length: int = helpers.ACCOUNT_INFO_LAYOUT.sizeof(),
    state: tp.Optional[str] = helpers.SOLCommitmentState.CONFIRMED,
) -> bytes:
    """Request account info"""
    if isinstance(account, OperatorAccount):
        account = account.public_key
    for _ in range(5):
        try:
            resp = await sol_client.get_account_info(account, commitment=state)
            resp = resp["result"].get("value")
            break
        except Exception:
            await asyncio.sleep(1)
    else:
        raise AssertionError(f"Account {account} doesn't exist")

    data = base64.b64decode(resp["data"][0])
    if len(data) < expected_length:
        raise Exception(f"Wrong data length for account data {account}")
    return data


async def get_transaction_count(sol_client, account: tp.Union[str, PublicKey, OperatorAccount]) -> int:
    """Get transactions count from account info"""
    info = helpers.AccountInfo.from_bytes(await get_account_data(sol_client, account))
    return int.from_bytes(info.trx_count, "little")


async def prepare_operators():
    print("Prepare operators")
    for i in range(OPERATORS_OFFSET, OPERATORS_COUNT + OPERATORS_OFFSET):
        op = TransactionSigner(OperatorAccount(i), helpers.create_treasury_pool_address("night-stand", EVM_LOADER_ID, i))
        await OPERATORS_QUEUE.put(op)
    print("Operators prepared")


async def prepare_users():
    web = web3.Web3()
    print("Prepare users")
    for i in range(0, PREPARED_USERS_COUNT+1):
        user = web.eth.account.from_key(ACCOUNT_ETH_BASE + PREPARED_USERS_OFFSET + i)
        solana_address, bump = ether2solana(user.address)
        await USERS_QUEUE.put(ETHUser(user, solana_address, 0))
    print("Users prepare complete")


async def send_trx(sol_client):
    token_sender = await USERS_QUEUE.get()
    token_receiver = await USERS_QUEUE.get()
    operator = await OPERATORS_QUEUE.get()

    if token_sender.nonce is None or token_sender.nonce == 0:
        token_sender.nonce = await get_transaction_count(sol_client, token_sender.sol_account)
    eth_transaction = make_eth_transaction(
        token_receiver.eth_account.address,
        data=b"",
        signer=token_sender.eth_account,
        value=random.randint(1, 10000),
        nonce=token_sender.nonce,
    )

    token_sender.nonce += 1
    trx = helpers.TransactionWithComputeBudget().add(
        make_TransactionExecuteFromInstruction(
            eth_transaction.rawTransaction,
            operator.operator,
            operator.treasury_pool.account,
            operator.treasury_pool.buffer,
            [token_sender.sol_account, token_receiver.sol_account],
        )
    )
    transaction_receipt = await sol_client.send_transaction(
        trx,
        operator.operator,
        opts=TxOpts(
            skip_confirmation=True, skip_preflight=True
        )
    )
    # print(f"## Token transfer transaction hash: {transaction_receipt}")
    await USERS_QUEUE.put(token_receiver)
    await USERS_QUEUE.put(token_sender)
    await OPERATORS_QUEUE.put(operator)


async def main_loop():
    loop = asyncio.get_event_loop()
    sol_client = AsyncClient(SOLANA_URL)
    while True:
        # recent_blockhash = await sol_client.get_recent_blockhash()
        tasks = [loop.create_task(send_trx(sol_client)) for _ in range(10000)]
        await asyncio.gather(*tasks)


loop = asyncio.get_event_loop()
loop.run_until_complete(prepare_operators())
loop.run_until_complete(prepare_users())
print(f"Users q: {USERS_QUEUE.qsize()}  Operators q: {OPERATORS_QUEUE.qsize()}")
loop.run_until_complete(main_loop())
loop.run_forever()
