import logging
import inspect
import os
import random
import string
import time
import allure
import typing as tp

import base58
import pytest
from _pytest.config import Config
from eth_account.signers.local import LocalAccount
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc import commitment
from solana.rpc.types import TxOpts
from web3.contract import Contract

from clickfile import EnvName
from utils.accounts import EthAccounts

from utils.apiclient import JsonRPCSession
from utils.consts import COUNTER_ID, LAMPORT_PER_SOL, MULTITOKEN_MINTS
from utils.erc20 import ERC20
from utils.erc20wrapper import ERC20Wrapper
from utils.evm_loader import EvmLoader
from utils.operator import Operator
from utils.solana_client import SolanaClient
from utils.prices import get_sol_price
from utils.web3client import NeonChainWeb3Client, Web3Client

log = logging.getLogger(__name__)

NEON_AIRDROP_AMOUNT = 1_000


@pytest.fixture(scope="session")
def ws_subscriber_url(pytestconfig: tp.Any) -> tp.Optional[str]:
    return pytestconfig.environment.ws_subscriber_url


@pytest.fixture(scope="session")
def json_rpc_client(pytestconfig: Config) -> JsonRPCSession:
    return JsonRPCSession(pytestconfig.environment.proxy_url)


@pytest.fixture(scope="class")
def web3_client(request, web3_client_session) -> NeonChainWeb3Client:
    if inspect.isclass(request.cls):
        request.cls.web3_client = web3_client_session
    yield web3_client_session


@pytest.fixture(scope="class")
def sol_client(request, sol_client_session) -> SolanaClient:
    if inspect.isclass(request.cls):
        request.cls.sol_client = sol_client_session
    yield sol_client_session


@pytest.fixture(scope="session")
def web3_client_sol(pytestconfig: Config) -> tp.Union[Web3Client, None]:
    if "sol" in pytestconfig.environment.network_ids:
        client = Web3Client(f"{pytestconfig.environment.proxy_url}/sol")
        return client
    else:
        return None


@pytest.fixture(scope="session")
def web3_client_usdt(pytestconfig: Config) -> tp.Union[Web3Client, None]:
    if "usdt" in pytestconfig.environment.network_ids:
        return Web3Client(f"{pytestconfig.environment.proxy_url}/usdt")
    else:
        return None


@pytest.fixture(scope="session", autouse=True)
def web3_client_eth(pytestconfig: Config) -> tp.Union[Web3Client, None]:
    if "eth" in pytestconfig.environment.network_ids:
        return Web3Client(f"{pytestconfig.environment.proxy_url}/eth")
    else:
        return None


@pytest.fixture(scope="session", autouse=True)
def operator(pytestconfig: Config, web3_client_session: NeonChainWeb3Client) -> Operator:
    return Operator(
        pytestconfig.environment.proxy_url,
        pytestconfig.environment.solana_url,
        pytestconfig.environment.spl_neon_mint,
        web3_client=web3_client_session,
        evm_loader=pytestconfig.environment.evm_loader,
    )


@pytest.fixture(scope="session")
def bank_account(pytestconfig: Config) -> tp.Optional[Keypair]:
    account = None
    if pytestconfig.environment.use_bank:
        if pytestconfig.getoption("--network") == "devnet":
            private_key = os.environ.get("BANK_PRIVATE_KEY")
        elif pytestconfig.getoption("--network") == "mainnet":
            private_key = os.environ.get("BANK_PRIVATE_KEY_MAINNET")
        key = base58.b58decode(private_key)
        account = Keypair.from_secret_key(key)
    yield account


@pytest.fixture(scope="session")
def eth_bank_account(pytestconfig: Config, web3_client_session) -> tp.Optional[Keypair]:
    account = None
    if pytestconfig.environment.eth_bank_account != "":
        account = web3_client_session.eth.account.from_key(pytestconfig.environment.eth_bank_account)
    if pytestconfig.getoption("--network") == "mainnet":
        account = web3_client_session.eth.account.from_key(os.environ.get("ETH_BANK_PRIVATE_KEY_MAINNET"))
    yield account


@pytest.fixture(scope="session")
def solana_account(bank_account, pytestconfig: Config, sol_client_session):
    account = Keypair.generate()

    if pytestconfig.environment.use_bank:
        sol_client_session.send_sol(bank_account, account.public_key, int(0.5 * LAMPORT_PER_SOL))
    else:
        sol_client_session.request_airdrop(account.public_key, 1 * LAMPORT_PER_SOL)
    yield account
    if pytestconfig.environment.use_bank:
        balance = sol_client_session.get_balance(account.public_key, commitment=commitment.Confirmed).value
        try:
            sol_client_session.send_sol(account, bank_account.public_key, balance - 5000)
        except:
            pass


@pytest.fixture(scope="function")
def new_solana_account(bank_account, pytestconfig: Config, sol_client_session):
    account = Keypair.generate()
    if pytestconfig.environment.use_bank:
        sol_client_session.send_sol(bank_account, account.public_key, int(0.01 * LAMPORT_PER_SOL))
    else:
        sol_client_session.request_airdrop(account.public_key, 1 * LAMPORT_PER_SOL)
    yield account
    if pytestconfig.environment.use_bank:
        balance = sol_client_session.get_balance(account.public_key, commitment=commitment.Confirmed).value
        try:
            sol_client_session.send_sol(account, bank_account.public_key, balance - 5000)
        except:
            pass


@pytest.fixture(scope="class")
def accounts(request, accounts_session, web3_client_session, pytestconfig: Config, eth_bank_account):
    if inspect.isclass(request.cls):
        request.cls.accounts = accounts_session
    yield accounts_session
    if pytestconfig.getoption("--network") == "mainnet":
        if len(accounts_session.accounts_collector) > 0:
            for item in accounts_session.accounts_collector:
                with allure.step(f"Restoring eth account balance from {item.key.hex()} account"):
                    web3_client_session.send_all_neons(item, eth_bank_account)
    accounts_session._accounts = []


@pytest.fixture(scope="session")
def erc20_spl(
    web3_client_session: NeonChainWeb3Client,
    faucet,
    pytestconfig: Config,
    sol_client_session,
    solana_account,
    eth_bank_account,
    accounts_session,
):
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(
        web3_client_session,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client_session,
        solana_account=solana_account,
        mintable=False,
        bank_account=eth_bank_account,
        account=accounts_session[0],
        evm_loader_id=pytestconfig.environment.evm_loader,
    )
    erc20.token_mint.approve(
        source=erc20.solana_associated_token_acc,
        delegate=sol_client_session.get_erc_auth_address(
            erc20.account.address,
            erc20.contract.address,
            pytestconfig.environment.evm_loader,
        ),
        owner=erc20.solana_acc.public_key,
        amount=1000000000000000,
        opts=TxOpts(preflight_commitment=commitment.Confirmed, skip_confirmation=False),
    )

    erc20.claim(erc20.account, bytes(erc20.solana_associated_token_acc), 100000000000000)
    yield erc20


@pytest.fixture(scope="session")
def erc20_simple(web3_client_session, faucet, accounts_session, eth_bank_account):
    erc20 = ERC20(
        web3_client=web3_client_session, faucet=faucet, bank_account=eth_bank_account, owner=accounts_session[0]
    )
    yield erc20


@pytest.fixture(scope="session")
def erc20_spl_mintable(
    web3_client_session: NeonChainWeb3Client,
    faucet,
    sol_client_session,
    solana_account,
    accounts_session,
    eth_bank_account,
):
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(
        web3_client_session,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client_session,
        solana_account=solana_account,
        mintable=True,
        bank_account=eth_bank_account,
        account=accounts_session[0],
    )
    erc20.mint_tokens(erc20.account, erc20.account.address)
    yield erc20


@pytest.fixture(scope="class")
def class_account_sol_chain(
    evm_loader,
    solana_account,
    web3_client,
    web3_client_sol,
    faucet,
    eth_bank_account,
    bank_account,
    pytestconfig
) -> LocalAccount:
    account = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)
    if pytestconfig.environment.use_bank:
        evm_loader.send_sol(bank_account, solana_account.public_key, int(1 * LAMPORT_PER_SOL))
    else:
        evm_loader.request_airdrop(solana_account.public_key, 1 * LAMPORT_PER_SOL)
    evm_loader.deposit_wrapped_sol_from_solana_to_neon(
        solana_account,
        account,
        web3_client_sol.eth.chain_id,
        int(1 * LAMPORT_PER_SOL),
    )
    return account


@pytest.fixture(scope="class")
def evm_loader(pytestconfig):
    return EvmLoader(pytestconfig.environment.evm_loader, pytestconfig.environment.solana_url)


@pytest.fixture(scope="class")
def account_with_all_tokens(
    evm_loader,
    solana_account,
    web3_client,
    web3_client_usdt,
    web3_client_eth,
    web3_client_sol,
    pytestconfig,
    faucet,
    eth_bank_account,
    neon_mint,
    operator_keypair,
    evm_loader_keypair,
    bank_account,
):
    neon_account = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account, amount=500)
    if web3_client_sol:
        if pytestconfig.environment.use_bank:
            evm_loader.send_sol(bank_account, solana_account.public_key, int(1 * LAMPORT_PER_SOL))
        else:
            evm_loader.request_airdrop(solana_account.public_key, 1 * LAMPORT_PER_SOL)
        evm_loader.deposit_wrapped_sol_from_solana_to_neon(
            solana_account,
            neon_account,
            web3_client_sol.eth.chain_id,
            int(1 * LAMPORT_PER_SOL),
        )
    for client in [web3_client_usdt, web3_client_eth]:
        if client:
            if client == web3_client_usdt:
                mint = MULTITOKEN_MINTS["USDT"]
            else:
                mint = MULTITOKEN_MINTS["ETH"]
            token_mint = PublicKey(mint)

            evm_loader.mint_spl_to(token_mint, solana_account, 1000000000000000)

            evm_loader.sent_token_from_solana_to_neon(
                solana_account,
                token_mint,
                neon_account,
                100000000,
                client.eth.chain_id,
            )
    return neon_account


@pytest.fixture(scope="session")
def neon_mint(pytestconfig: Config):
    neon_mint = PublicKey(pytestconfig.environment.spl_neon_mint)
    return neon_mint


@pytest.fixture(scope="class")
def withdraw_contract(web3_client, faucet, accounts) -> Contract:
    contract, _ = web3_client.deploy_and_get_contract("precompiled/NeonToken", "0.8.10", account=accounts[1])
    return contract


@pytest.fixture(scope="class")
def common_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Common",
        version="0.8.12",
        contract_name="Common",
        account=accounts[0],
    )
    yield contract


@pytest.fixture(scope="class")
def meta_proxy_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract("./EIPs/MetaProxy", "0.8.10", account=accounts[0])
    return contract


@pytest.fixture(scope="class")
def event_caller_contract(web3_client, accounts) -> tp.Any:
    event_caller, _ = web3_client.deploy_and_get_contract("common/EventCaller", "0.8.12", accounts[0])
    yield event_caller


@pytest.fixture(scope="class")
def event_checker_callee_address(web3_client, accounts) -> tp.Any:
    _, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "common/EventsCheckerCallee", "0.8.15", account=accounts[0]
    )
    return contract_deploy_tx["contractAddress"]


@pytest.fixture(scope="class")
def opcodes_checker(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "opcodes/BaseOpCodes", "0.5.16", accounts[0], contract_name="BaseOpCodes"
    )
    return contract


@pytest.fixture(scope="class")
def eip1052_checker(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "EIPs/EIP1052Extcodehash",
        "0.8.10",
        accounts[0],
        contract_name="EIP1052Checker",
    )
    return contract


@pytest.fixture(scope="class")
def wsol(web3_client_sol, class_account_sol_chain):
    contract, _ = web3_client_sol.deploy_and_get_contract(
        contract="common/WNativeChainToken",
        version="0.8.12",
        contract_name="WNativeChainToken",
        account=class_account_sol_chain,
    )
    return contract


@pytest.fixture(scope="class")
def wneon(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        "common/WNeon", "0.4.26", account=accounts[0], contract_name="WNEON"
    )
    return contract


@pytest.fixture(scope="class")
def storage_contract(web3_client, accounts) -> tp.Any:
    contract, _ = web3_client.deploy_and_get_contract(
        "common/StorageSoliditySource",
        "0.8.8",
        accounts[0],
        contract_name="Storage",
        constructor_args=[],
    )
    yield contract


@pytest.fixture(scope="class")
def storage_contract_with_deploy_tx(web3_client, accounts) -> tp.Any:
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "common/StorageSoliditySource",
        "0.8.8",
        accounts[0],
        contract_name="Storage",
        constructor_args=[],
    )
    yield contract, contract_deploy_tx


@pytest.fixture(scope="class")
def revert_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Revert",
        version="0.8.10",
        contract_name="TrivialRevert",
        account=accounts[0],
    )
    yield contract


@pytest.fixture(scope="class")
def revert_contract_caller(web3_client, accounts, revert_contract):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Revert",
        version="0.8.10",
        contract_name="Caller",
        account=accounts[0],
        constructor_args=[revert_contract.address],
    )
    yield contract


@pytest.fixture(scope="session")
def sol_price() -> float:
    """Get SOL price from Solana mainnet"""
    price = get_sol_price()
    started = time.time()
    timeout = 120
    while price is None and (time.time() - started) < timeout:
        print("Can't get SOL price")
        time.sleep(3)
        price = get_sol_price()
    with allure.step(f"SOL price {price}$"):
        return price


@pytest.fixture(scope="session")
def neon_price(web3_client_session) -> float:
    """Get NEON price in usd"""
    price = web3_client_session.get_token_usd_gas_price()
    with allure.step(f"NEON price {price}$"):
        return price


@pytest.fixture(scope="class")
def events_checker_contract(web3_client, accounts) -> tp.Any:
    contract, _ = web3_client.deploy_and_get_contract("common/EventsCheckerCaller", "0.8.15", account=accounts[0])
    yield contract


@pytest.fixture(scope="class")
def counter_contract(web3_client, accounts):
    contract, _ = web3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=accounts[0])
    return contract


@pytest.fixture(scope="class")
def nested_call_contracts(accounts, web3_client):
    contract_a, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="A"
    )
    contract_b, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="B"
    )
    contract_c, _ = web3_client.deploy_and_get_contract(
        "common/NestedCallsChecker", "0.8.12", accounts[0], contract_name="C"
    )
    yield contract_a, contract_b, contract_c


@pytest.fixture(scope="function")
def recursion_factory(accounts, web3_client):
    sender_account = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract(
        "common/Recursion",
        "0.8.10",
        sender_account,
        contract_name="DeployRecursionFactory",
        constructor_args=[3],
    )
    yield contract


@pytest.fixture(scope="function")
def destroyable_contract(accounts, web3_client):
    sender_account = accounts[0]
    contract, _ = web3_client.deploy_and_get_contract(
        "opcodes/SelfDestroyable", "0.8.10", sender_account, "SelfDestroyable"
    )
    yield contract


@pytest.fixture(scope="class")
def expected_error_checker(accounts, web3_client):
    contract, _ = web3_client.deploy_and_get_contract(
        "common/ExpectedErrorsChecker", "0.8.12", accounts[0], contract_name="A"
    )
    yield contract


@pytest.fixture(scope="class")
def multiple_actions_erc721(web3_client, accounts):
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "EIPs/ERC721/MultipleActions", "0.8.10", accounts[0], contract_name="MultipleActionsERC721"
    )
    return accounts[0], contract


@pytest.fixture(scope="class")
def call_solana_caller(accounts, web3_client):
    contract, _ = web3_client.deploy_and_get_contract("precompiled/CallSolanaCaller.sol", "0.8.10", accounts[0])
    return contract


@pytest.fixture(scope="class")
def counter_resource_address(call_solana_caller, accounts, web3_client):
    tx = web3_client.make_raw_tx(accounts[0].address)
    salt = web3_client.text_to_bytes32("1")
    instruction_tx = call_solana_caller.functions.createResource(salt, 8, 100000, bytes(COUNTER_ID)).build_transaction(
        tx
    )
    web3_client.send_transaction(accounts[0], instruction_tx)
    yield call_solana_caller.functions.getResourceAddress(salt).call()


@pytest.fixture(scope="class")
def eip1559_setup(
        request: pytest.FixtureRequest,
        pytestconfig: Config,
        accounts_session: EthAccounts,
        web3_client_session: NeonChainWeb3Client,
        env_name: EnvName,
):
    """
    Creates type-2 transactions in the db
    """

    # Get the max value of marker @pytest.mark.need_eip1559_blocks(...) among selected tests in the class
    block_count = 1
    selected_tests_in_class = [item for item in request.session.items if item.cls is request.cls]  # noqa
    markers = request.cls.pytestmark + [mark for test in selected_tests_in_class for mark in test.own_markers]
    for marker in markers:
        if marker.name == "need_eip1559_blocks":
            need_eip1559_blocks = marker.args[0]
            block_count = max(block_count, need_eip1559_blocks)

    # Check if the latest blocks already have enough type-2 transactions. If that's the case - return
    fee_history = web3_client_session._web3.eth.fee_history(block_count, 'latest', None)  # noqa
    base_fee_per_gas_history = fee_history["baseFeePerGas"]
    if len(base_fee_per_gas_history) >= block_count + 1:
        return

    # Send the transactions
    sender = accounts_session[0]
    recipient = web3_client_session.create_account()
    gas_estimate: tp.Union[int, tp.Literal["auto"]] = "auto"
    value = 10

    for nonce in range(block_count):
        tx_params = web3_client_session.make_raw_tx_eip_1559(
            nonce=nonce,
            chain_id="auto",
            from_=sender.address,
            to=recipient.address,
            value=value,
            gas=gas_estimate,
            max_priority_fee_per_gas="auto",
            max_fee_per_gas="auto",
            access_list=None,
            data=None,
        )

        if gas_estimate == "auto":
            gas_estimate = int(tx_params["gas"])

        start = time.time()
        receipt = web3_client_session.send_transaction(account=sender, transaction=tx_params)
        assert receipt.status == 1

        # Sleep to make sure the next transaction goes to the next block
        min_pause = 3 if env_name is EnvName.GETH else 0.4
        pause = min_pause - (time.time() - start)
        if pause > 0:
            time.sleep(pause)
