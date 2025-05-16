import json
import pathlib
from typing import Tuple, Any

import allure
import eth_abi
import pytest
from eth_keys import keys as eth_keys
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from conftest import EnvironmentConfig
from utils.consts import OPERATOR_KEYPAIR_PATH, REMAPPING_ZEPPELIN
from utils.evm_loader import EvmLoader
from utils.solana_client import SolanaClient
from utils.types import Contract, Caller, TreasuryPool
from .utils.ethereum import make_contract_call_trx
from .utils.neon_api_client import NeonApiClient
from .utils.neon_api_rpc_client import NeonApiRpcClient
from .utils.transaction_checks import check_transaction_logs_have_text


def prepare_operator(key_file: pathlib.Path | str, evm_loader: EvmLoader) -> Keypair:
    chain_ids = (evm_loader.sol_chain_id, evm_loader.chain_id)
    with open(key_file, "r") as key:
        secret_key = json.load(key)
        account = Keypair.from_bytes(secret_key)

    evm_loader.request_airdrop(account.pubkey(), 1000 * 10**9, commitment=Confirmed)

    operator_ether = eth_keys.PrivateKey(account.secret()[:32]).public_key.to_canonical_address()
    for chain_id in chain_ids:
        ether_balance_pubkey = evm_loader.ether2operator_balance(account, operator_ether, chain_id)
        acc_info = evm_loader.get_account_info(ether_balance_pubkey, commitment=Confirmed)
        if acc_info.value is None:
            evm_loader.create_operator_balance_account(account, operator_ether, chain_id)

    return account


@pytest.fixture(scope="session")
def solana_client(environment: EnvironmentConfig):
    return SolanaClient(endpoint=environment.solana_url)


# following two keypair could be parametrized
@pytest.fixture(scope="session")
def operator_keypair(index_of_process: int, evm_loader: EvmLoader) -> Keypair:
    """
    Initialized solana keypair with balance. Get private keys from ci/operator-keypairs
    """
    key_file = pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id{index_of_process+1}.json")
    allure.attach(
        f"current key_file {key_file}",
        "Operator key",
        attachment_type=allure.attachment_type.TEXT,
    )
    return prepare_operator(key_file, evm_loader)


@pytest.fixture(scope="session")
def second_operator_keypair(index_of_process: int, evm_loader: EvmLoader) -> Keypair:
    """
    Initialized solana keypair with balance. Get private key from cli or ./ci/operator-keypairs
    """
    file_id = 20 + index_of_process
    key_file = pathlib.Path(f"{OPERATOR_KEYPAIR_PATH}/id{file_id}.json")
    allure.attach(
        f"current key_file {key_file}",
        "Operator key",
        attachment_type=allure.attachment_type.TEXT,
    )
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
def sender_with_tokens(evm_loader: EvmLoader, operator_keypair: Keypair) -> Caller:
    user = evm_loader.make_new_user(operator_keypair)
    evm_loader.deposit_neon(operator_keypair, user.eth_address, 100000)
    return user


@pytest.fixture(scope="session")
def sender_with_wsol(evm_loader: EvmLoader, operator_keypair: Keypair) -> Caller:
    user = evm_loader.make_new_user(operator_keypair)
    evm_loader.deposit_wrapped_sol_from_solana_to_neon(
        solana_account=user.solana_account,
        neon_account="0x" + user.eth_address.hex(),
        full_amount=100000,
    )

    return user


@pytest.fixture(scope="session")
def holder_acc(operator_keypair: Keypair, evm_loader: EvmLoader) -> Pubkey:
    return evm_loader.create_holder(operator_keypair)


@pytest.fixture(scope="function")
def new_holder_acc(operator_keypair: Keypair, evm_loader: EvmLoader) -> Pubkey:
    return evm_loader.create_holder(operator_keypair)


@pytest.fixture(scope="function")
def new_holder_acc_2(operator_keypair: Keypair, evm_loader: EvmLoader) -> Pubkey:
    return evm_loader.create_holder(operator_keypair)


@pytest.fixture(scope="function")
def rw_lock_contract(
    evm_loader: EvmLoader,
    operator_keypair: Keypair,
    neon_api_client: NeonApiClient,
    session_user: Caller,
    treasury_pool: TreasuryPool,
) -> Contract:
    return evm_loader.deploy_contract(operator_keypair, session_user, "rw_lock", neon_api_client, treasury_pool)


@pytest.fixture(scope="function")
def rw_lock_caller(
    evm_loader: EvmLoader,
    operator_keypair: Keypair,
    session_user: Caller,
    treasury_pool: TreasuryPool,
    rw_lock_contract: Contract,
    neon_api_client: NeonApiClient,
) -> Contract:
    constructor_args = eth_abi.encode(["address"], [rw_lock_contract.eth_address.hex()])
    return evm_loader.deploy_contract(
        operator_keypair,
        session_user,
        "rw_lock",
        neon_api_client,
        treasury_pool,
        encoded_args=constructor_args,
        contract_name="rw_lock_caller",
    )


@pytest.fixture(scope="function")
def string_setter_contract(
    evm_loader: EvmLoader,
    operator_keypair: Keypair,
    session_user: Caller,
    treasury_pool: TreasuryPool,
    neon_api_client: NeonApiClient,
) -> Contract:
    return evm_loader.deploy_contract(operator_keypair, session_user, "string_setter", neon_api_client, treasury_pool)


@pytest.fixture(scope="function")
def basic_contract(
    evm_loader: EvmLoader,
    operator_keypair: Keypair,
    session_user: Caller,
    treasury_pool: TreasuryPool,
    neon_api_client: NeonApiClient,
) -> Contract:
    return evm_loader.deploy_contract(
        operator_keypair,
        session_user,
        "common/Common",
        neon_api_client,
        treasury_pool,
        version="0.8.12",
    )


@pytest.fixture(scope="function")
def spl_token_caller(operator_keypair, evm_loader, session_user, treasury_pool, neon_api_client) -> Contract:
    return evm_loader.deploy_contract(
        operator_keypair,
        session_user,
        "precompiled/SplTokenCaller",
        neon_api_client,
        treasury_pool,
        version="0.8.28",
    )


@pytest.fixture(scope="session")
def calculator_contract(
    evm_loader: EvmLoader,
    neon_api_client: NeonApiClient,
    operator_keypair: Keypair,
    session_user: Caller,
    treasury_pool: TreasuryPool,
) -> Contract:
    return evm_loader.deploy_contract(operator_keypair, session_user, "calculator", neon_api_client, treasury_pool)


@pytest.fixture(scope="session")
def calculator_caller_contract(
    evm_loader: EvmLoader,
    operator_keypair: Keypair,
    session_user: Caller,
    treasury_pool,
    calculator_contract,
    neon_api_client: NeonApiClient,
) -> Contract:
    constructor_args = eth_abi.encode(["address"], [calculator_contract.eth_address.hex()])

    return evm_loader.deploy_contract(
        operator_keypair,
        session_user,
        "calculator",
        neon_api_client,
        treasury_pool,
        encoded_args=constructor_args,
        contract_name="calculatorCaller",
    )


@pytest.fixture(scope="session")
def erc20_for_spl_factory_contract(
    operator_keypair, evm_loader, sender_with_tokens, treasury_pool, neon_api_client, holder_acc
):
    return evm_loader.deploy_contract(
        operator_keypair,
        sender_with_tokens,
        "external/neon-contracts/contracts/token/ERC20ForSpl/erc20_for_spl_factory",
        neon_api_client,
        treasury_pool,
        contract_name="ERC20ForSplFactory",
        version="0.8.28",
        import_remappings=REMAPPING_ZEPPELIN,
    )


@pytest.fixture(scope="session")
def multiple_actions_erc20(
    operator_keypair: Keypair,
    evm_loader: EvmLoader,
    sender_with_tokens: Caller,
    treasury_pool: TreasuryPool,
    neon_api_client: NeonApiClient,
    holder_acc: Pubkey,
) -> Contract:
    encoded_args = eth_abi.encode(["string", "string", "uint256"], ["Test TTT", "TTT", 9])
    return evm_loader.deploy_contract(
        operator=operator_keypair,
        user=sender_with_tokens,
        contract_file_name="EIPs/ERC20/MultipleActions",
        neon_api_client=neon_api_client,
        treasury_pool=treasury_pool,
        contract_name="MultipleActionsERC20",
        version="0.8.28",
        encoded_args=encoded_args,
        import_remappings=REMAPPING_ZEPPELIN,
    )


@pytest.fixture(scope="session")
def neon_rpc_client(environment: EnvironmentConfig) -> NeonApiRpcClient:
    return NeonApiRpcClient(url=environment.neon_core_api_rpc_url, chain_id=environment.network_ids["neon"])


@pytest.fixture(scope="session")
def neon_api_client(environment: EnvironmentConfig) -> NeonApiClient:
    return NeonApiClient(
        url=environment.neon_core_api_url,
        chain_id=environment.network_ids["neon"],
        sol_chain_id=environment.network_ids["sol"],
    )


@pytest.fixture(scope="session")
def query_account_caller_contract(
    operator_keypair, evm_loader, sender_with_tokens, treasury_pool, neon_api_client, holder_acc
):
    return evm_loader.deploy_contract(
        operator=operator_keypair,
        user=sender_with_tokens,
        contract_file_name="precompiled/QueryAccountCaller.sol",
        neon_api_client=neon_api_client,
        treasury_pool=treasury_pool,
        contract_name="QueryAccountCaller",
        version="0.8.10",
    )


@pytest.fixture(scope="session")
def erc20_for_spl(
    evm_loader,
    operator_keypair,
    sender_with_tokens,
    treasury_pool,
    neon_api_client,
    holder_acc,
    proxy_contract,
    sol_client,
) -> Tuple[Any, Any]:
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

    check_transaction_logs_have_text(solana_client=sol_client, trx=resp, text="exit_status=0x12")
    byte_data = bytes.fromhex(emulate_result["result"])
    decoded_data = eth_abi.decode(["bytes32", "address"], byte_data)
    token_mint = decoded_data[0]
    erc20_for_spl_address = decoded_data[1]
    return token_mint, erc20_for_spl_address
