import json
import pathlib

import eth_abi
import pytest
from solders.keypair import Keypair
from eth_keys import keys as eth_keys
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed

from utils.consts import OPERATOR_KEYPAIR_PATH
from utils.evm_loader import EvmLoader
from utils.types import Contract, Caller, TreasuryPool
from utils.neon_user import NeonUser
from .utils.constants import NEON_CORE_API_URL, NEON_CORE_API_RPC_URL, SOLANA_URL, EVM_LOADER, SOL_CHAIN_ID, CHAIN_ID
from .utils.contract import deploy_contract, make_contract_call_trx
from .utils.neon_api_rpc_client import NeonApiRpcClient
from .utils.storage import create_holder
from .utils.neon_api_client import NeonApiClient
from .utils.transaction_checks import check_transaction_logs_have_text


@pytest.fixture(scope="session")
def evm_loader() -> EvmLoader:
    loader = EvmLoader(EVM_LOADER, SOLANA_URL)
    return loader


def prepare_operator(key_file, evm_loader: EvmLoader):
    with open(key_file, "r") as key:
        secret_key = json.load(key)
        account = Keypair.from_bytes(secret_key)

    evm_loader.request_airdrop(account.pubkey(), 1000 * 10**9, commitment=Confirmed)

    operator_ether = eth_keys.PrivateKey(account.secret()[:32]).public_key.to_canonical_address()
    for chain_id in (SOL_CHAIN_ID, CHAIN_ID):
        ether_balance_pubkey = evm_loader.ether2operator_balance(account, operator_ether, chain_id)
        acc_info = evm_loader.get_account_info(ether_balance_pubkey, commitment=Confirmed)
        if acc_info.value is None:
            evm_loader.create_operator_balance_account(account, operator_ether, chain_id)

    return account


@pytest.fixture(scope="session")
def default_operator_keypair(evm_loader: EvmLoader) -> Keypair:
    """
    Initialized solana keypair with balance. Get private keys from ci/operator-keypairs/id.json
    """
    key_file = pathlib.Path(OPERATOR_KEYPAIR_PATH / "id.json")
    return prepare_operator(key_file, evm_loader)


@pytest.fixture(scope="session")
def operator_keypair(worker_id, evm_loader) -> Keypair:
    """
    Initialized solana keypair with balance. Get private keys from ci/operator-keypairs
    """
    if worker_id in ("master", "gw1"):
        key_file = pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id.json")
    else:
        file_id = int(worker_id[-1]) + 2
        key_file = pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id{file_id}.json")
    return prepare_operator(key_file, evm_loader)


@pytest.fixture(scope="session")
def second_operator_keypair(worker_id, evm_loader) -> Keypair:
    """
    Initialized solana keypair with balance. Get private key from cli or ./ci/operator-keypairs
    """
    if worker_id in ("master", "gw1"):
        key_file = pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id20.json")
    else:
        file_id = 20 + int(worker_id[-1]) + 2
        key_file = pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id{file_id}.json")

    return prepare_operator(key_file, evm_loader)


@pytest.fixture(scope="function")
def user_account(evm_loader, operator_keypair) -> Caller:
    return evm_loader.make_new_user(operator_keypair)


@pytest.fixture(scope="session")
def session_user(evm_loader, operator_keypair) -> Caller:
    return evm_loader.make_new_user(operator_keypair)


@pytest.fixture(scope="session")
def second_session_user(evm_loader, operator_keypair) -> Caller:
    return evm_loader.make_new_user(operator_keypair)


@pytest.fixture(scope="session")
def sender_with_tokens(evm_loader, operator_keypair) -> Caller:
    user = evm_loader.make_new_user(operator_keypair)
    evm_loader.deposit_neon(operator_keypair, user.eth_address, 100000)
    return user


@pytest.fixture(scope="session")
def sender_with_wsol(evm_loader, operator_keypair) -> Caller:
    user = evm_loader.make_new_user(operator_keypair)
    evm_loader.deposit_wrapped_sol_from_solana_to_neon(
        user.solana_account, "0x" + user.eth_address.hex(), SOL_CHAIN_ID, 100000
    )
    return user


@pytest.fixture(scope="session")
def holder_acc(operator_keypair: Keypair, evm_loader: EvmLoader) -> Pubkey:
    return create_holder(operator_keypair, evm_loader)


@pytest.fixture(scope="function")
def new_holder_acc(operator_keypair, evm_loader) -> Pubkey:
    return create_holder(operator_keypair, evm_loader)


@pytest.fixture(scope="function")
def rw_lock_contract(evm_loader: EvmLoader, operator_keypair: Keypair, session_user: Caller, treasury_pool) -> Contract:
    return deploy_contract(operator_keypair, session_user, "rw_lock", evm_loader, treasury_pool)


@pytest.fixture(scope="function")
def rw_lock_caller(
    evm_loader: EvmLoader,
    operator_keypair: Keypair,
    session_user: Caller,
    treasury_pool: TreasuryPool,
    rw_lock_contract: Contract,
) -> Contract:
    constructor_args = eth_abi.encode(["address"], [rw_lock_contract.eth_address.hex()])
    return deploy_contract(
        operator_keypair,
        session_user,
        "rw_lock",
        evm_loader,
        treasury_pool,
        encoded_args=constructor_args,
        contract_name="rw_lock_caller",
    )


@pytest.fixture(scope="function")
def string_setter_contract(
    evm_loader: EvmLoader, operator_keypair: Keypair, session_user: Caller, treasury_pool
) -> Contract:
    return deploy_contract(operator_keypair, session_user, "string_setter", evm_loader, treasury_pool)


@pytest.fixture(scope="function")
def basic_contract(evm_loader, operator_keypair, session_user, treasury_pool) -> Contract:
    return deploy_contract(operator_keypair, session_user, "common/Common", evm_loader, treasury_pool, version="0.8.12")


@pytest.fixture(scope="function")
def spl_token_caller(operator_keypair, evm_loader, session_user, treasury_pool):
    return deploy_contract(
        operator_keypair,
        session_user,
        "precompiled/SplTokenCaller",
        evm_loader,
        treasury_pool,
        chain_id=CHAIN_ID,
        version="0.8.12",
    )


@pytest.fixture(scope="session")
def calculator_contract(
    evm_loader: EvmLoader, operator_keypair: Keypair, session_user: Caller, treasury_pool
) -> Contract:
    return deploy_contract(operator_keypair, session_user, "calculator", evm_loader, treasury_pool)


@pytest.fixture(scope="session")
def calculator_caller_contract(
    evm_loader: EvmLoader, operator_keypair: Keypair, session_user: Caller, treasury_pool, calculator_contract
) -> Contract:
    constructor_args = eth_abi.encode(["address"], [calculator_contract.eth_address.hex()])

    return deploy_contract(
        operator_keypair,
        session_user,
        "calculator",
        evm_loader,
        treasury_pool,
        encoded_args=constructor_args,
        contract_name="calculatorCaller",
    )


@pytest.fixture(scope="session")
def erc20_for_spl_factory_contract(
    operator_keypair, evm_loader, sender_with_tokens, treasury_pool, neon_api_client, holder_acc
):
    return deploy_contract(
        operator_keypair,
        sender_with_tokens,
        "external/neon-evm/erc20_for_spl_factory",
        evm_loader,
        treasury_pool,
        contract_name="ERC20ForSplFactory",
        version="0.8.24",
    )


@pytest.fixture(scope="session")
def erc20_for_spl(
    evm_loader, operator_keypair, sender_with_tokens, treasury_pool, neon_api_client, holder_acc, proxy_contract
):
    emulate_result = neon_api_client.emulate_contract_call(
        sender_with_tokens.eth_address.hex(),
        proxy_contract.eth_address.hex(),
        "deploy(string,string,string,uint8)",
        ["Test", "TTT", "http://uri.com", 9],
    )
    additional_accounts = [Pubkey.from_string(item["pubkey"]) for item in emulate_result["solana_accounts"]]
    signed_tx = make_contract_call_trx(
        evm_loader,
        sender_with_tokens,
        proxy_contract,
        "deploy(string,string,string,uint8)",
        ["Test", "TTT", "http://uri.com", 9],
    )
    evm_loader.write_transaction_to_holder_account(signed_tx, holder_acc, operator_keypair)

    resp = evm_loader.execute_transaction_steps_from_account(
        operator_keypair,
        treasury_pool,
        holder_acc,
        additional_accounts,
    )

    check_transaction_logs_have_text(resp, "exit_status=0x12")
    byte_data = bytes.fromhex(emulate_result["result"])
    decoded_data = eth_abi.decode(["bytes32", "address"], byte_data)
    token_mint = decoded_data[0]
    erc20_for_spl_address = decoded_data[1]
    return token_mint, erc20_for_spl_address


@pytest.fixture(scope="session")
def neon_api_client():
    client = NeonApiClient(url=NEON_CORE_API_URL)
    return client


@pytest.fixture(scope="session")
def neon_rpc_client():
    client = NeonApiRpcClient(url=NEON_CORE_API_RPC_URL)
    return client
