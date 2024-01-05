import os
import random
import string
import pathlib
import inspect
import json
import typing as tp

import allure
import base58
import pytest
from _pytest.config import Config
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc import commitment
from solana.rpc.types import TxOpts

from utils.apiclient import JsonRPCSession
from utils.consts import LAMPORT_PER_SOL, Unit
from utils.erc20 import ERC20
from utils.erc20wrapper import ERC20Wrapper
from utils.operator import Operator
from utils.web3client import NeonChainWeb3Client, Web3Client
from utils.prices import get_sol_price, get_neon_price

NEON_AIRDROP_AMOUNT = 10_000


def pytest_collection_modifyitems(config, items):
    deselected_items = []
    selected_items = []
    deselected_marks = []
    network_name = config.getoption("--network")

    if network_name == "devnet":
        deselected_marks.append("only_stands")
    else:
        deselected_marks.append("only_devnet")

    envs_file = config.getoption("--envs")
    with open(pathlib.Path().parent.parent / envs_file, "r+") as f:
        environments = json.load(f)

    if len(environments[network_name]["network_ids"]) == 1:
        deselected_marks.append("multipletokens")
    for item in items:
        if any([item.get_closest_marker(mark) for mark in deselected_marks]):
            deselected_items.append(item)
        else:
            selected_items.append(item)

    config.hook.pytest_deselected(items=deselected_items)
    items[:] = selected_items


@pytest.fixture(scope="session")
def ws_subscriber_url(pytestconfig: tp.Any) -> tp.Optional[str]:
    return pytestconfig.environment.ws_subscriber_url


@pytest.fixture(scope="session")
def json_rpc_client(pytestconfig: Config) -> JsonRPCSession:
    return JsonRPCSession(pytestconfig.environment.proxy_url)


@pytest.fixture(scope="class")
def web3_client(request, web3_client_session):
    if inspect.isclass(request.cls):
        request.cls.web3_client = web3_client_session
    yield web3_client_session


@pytest.fixture(scope="class")
def sol_client(request, sol_client_session):
    if inspect.isclass(request.cls):
        request.cls.sol_client = sol_client_session
    yield sol_client_session


@pytest.fixture(scope="session", autouse=True)
def web3_client_sol(pytestconfig: Config) -> tp.Union[Web3Client, None]:
    if "sol" in pytestconfig.environment.network_ids:
        client = Web3Client(f"{pytestconfig.environment.proxy_url}/sol")
        return client
    else:
        return None


@pytest.fixture(scope="session")
def web3_client_abc(pytestconfig: Config) -> tp.Union[Web3Client, None]:
    if "abc" in pytestconfig.environment.network_ids:
        return Web3Client(f"{pytestconfig.environment.proxy_url}/abc")
    else:
        return None


@pytest.fixture(scope="session", autouse=True)
def web3_client_def(pytestconfig: Config) -> tp.Union[Web3Client, None]:
    if "def" in pytestconfig.environment.network_ids:
        return Web3Client(f"{pytestconfig.environment.proxy_url}/def")
    else:
        return None


@pytest.fixture(scope="session", autouse=True)
def operator(pytestconfig: Config, web3_client_session: NeonChainWeb3Client) -> Operator:
    return Operator(
        pytestconfig.environment.proxy_url,
        pytestconfig.environment.solana_url,
        pytestconfig.environment.operator_neon_rewards_address,
        pytestconfig.environment.spl_neon_mint,
        pytestconfig.environment.operator_keys,
        web3_client=web3_client_session,
    )


@pytest.fixture(scope="class")
def prepare_account(operator, faucet, web3_client: NeonChainWeb3Client):
    """Create new account for tests and save operator pre and post balances"""
    with allure.step("Create account for tests"):
        acc = web3_client.eth.account.create()
    with allure.step(f"Request {NEON_AIRDROP_AMOUNT} NEON from faucet for {acc.address}"):
        faucet.request_neon(acc.address, NEON_AIRDROP_AMOUNT)
        assert web3_client.get_balance(acc, Unit.ETHER) == NEON_AIRDROP_AMOUNT
    start_neon_balance = operator.get_token_balance()
    start_sol_balance = operator.get_solana_balance()
    with allure.step(
        f"Operator initial balance: {start_neon_balance / LAMPORT_PER_SOL} NEON {start_sol_balance / LAMPORT_PER_SOL} SOL"
    ):
        pass
    yield acc
    end_neon_balance = operator.get_token_balance()
    end_sol_balance = operator.get_solana_balance()
    with allure.step(
        f"Operator end balance: {end_neon_balance / LAMPORT_PER_SOL} NEON {end_sol_balance / LAMPORT_PER_SOL} SOL"
    ):
        pass
    with allure.step(f"Account end balance: {web3_client.get_balance(acc, Unit.ETHER)} NEON"):
        pass


@pytest.fixture(scope="session")
def bank_account(pytestconfig: Config) -> tp.Optional[Keypair]:
    account = None
    if pytestconfig.environment.use_bank:
        private_key = os.environ.get("BANK_PRIVATE_KEY")
        key = base58.b58decode(private_key)
        account = Keypair.from_secret_key(key)
    yield account


@pytest.fixture(scope="session")
def eth_bank_account(pytestconfig: Config, web3_client_session) -> tp.Optional[Keypair]:
    account = None
    if pytestconfig.environment.eth_bank_account != "":
        account = web3_client_session.eth.account.from_key(pytestconfig.environment.eth_bank_account)
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


@pytest.fixture(scope="class")
def accounts(request, accounts_session):
    if inspect.isclass(request.cls):
        request.cls.accounts = accounts_session
    yield accounts_session
    accounts_session._accounts = []


@pytest.fixture(scope="session")
def erc20_spl(
    web3_client_session: NeonChainWeb3Client,
    faucet,
    pytestconfig: Config,
    sol_client_session,
    solana_account,
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
def erc20_simple(web3_client_session, faucet):
    erc20 = ERC20(web3_client_session, faucet)
    return erc20


@pytest.fixture(scope="session")
def erc20_spl_mintable(web3_client_session: NeonChainWeb3Client, faucet, sol_client_session, solana_account):
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(
        web3_client_session,
        faucet,
        f"Test {symbol}",
        symbol,
        sol_client_session,
        solana_account=solana_account,
        mintable=True,
    )
    erc20.mint_tokens(erc20.account, erc20.account.address)
    yield erc20


@pytest.fixture(scope="function")
def new_account(web3_client_session, faucet, eth_bank_account):
    account = web3_client_session.create_account_with_balance(faucet, bank_account=eth_bank_account)
    yield account


@pytest.fixture(scope="class")
def class_account(
    web3_client,
    faucet,
    eth_bank_account,
    solana_account,
    sol_client_session,
    web3_client_sol,
    pytestconfig,
):
    account = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)
    yield account


@pytest.fixture(scope="class")
def class_account_sol_chain(
    sol_client_session,
    solana_account,
    web3_client,
    web3_client_sol,
    pytestconfig,
    faucet,
    eth_bank_account,
):
    account = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)
    sol_client_session.request_airdrop(solana_account.public_key, 1 * LAMPORT_PER_SOL)
    sol_client_session.deposit_wrapped_sol_from_solana_to_neon(
        solana_account,
        account,
        web3_client_sol.eth.chain_id,
        pytestconfig.environment.evm_loader,
        1 * LAMPORT_PER_SOL,
    )
    return account


@pytest.fixture(scope="class")
def account_with_all_tokens(
    sol_client_session,
    solana_account,
    web3_client,
    web3_client_abc,
    web3_client_def,
    web3_client_sol,
    pytestconfig,
    faucet,
    eth_bank_account,
    neon_mint,
    operator_keypair,
    evm_loader_keypair,
):
    account = web3_client.create_account_with_balance(faucet, bank_account=eth_bank_account)
    if web3_client_sol:
        sol_client_session.request_airdrop(solana_account.public_key, 1 * LAMPORT_PER_SOL)
        sol_client_session.deposit_wrapped_sol_from_solana_to_neon(
            solana_account,
            account,
            web3_client_sol.eth.chain_id,
            pytestconfig.environment.evm_loader,
            1 * LAMPORT_PER_SOL,
        )
    for client in [web3_client_abc, web3_client_def]:
        if client:
            new_sol_account = Keypair.generate()
            sol_client_session.send_sol(solana_account, new_sol_account.public_key, 5000000)
            sol_client_session.deposit_neon_like_tokens_from_solana_to_neon(
                neon_mint,
                new_sol_account,
                account,
                client.eth.chain_id,
                operator_keypair,
                evm_loader_keypair,
                pytestconfig.environment.evm_loader,
                1000000000000000000,
            )
    return account


@pytest.fixture(scope="function")
def new_account_zero_balance(web3_client):
    new_acc = web3_client.create_account()
    yield new_acc


@pytest.fixture(scope="session")
def neon_mint(pytestconfig: Config):
    neon_mint = PublicKey(pytestconfig.environment.spl_neon_mint)
    return neon_mint


@pytest.fixture(scope="class")
def withdraw_contract(web3_client, faucet, class_account):
    contract, _ = web3_client.deploy_and_get_contract("precompiled/NeonToken", "0.8.10", account=class_account)
    return contract


@pytest.fixture(scope="class")
def common_contract(web3_client, class_account):
    contract, _ = web3_client.deploy_and_get_contract(
        contract="common/Common",
        version="0.8.12",
        contract_name="Common",
        account=class_account,
    )
    yield contract


@pytest.fixture(scope="class")
def meta_proxy_contract(web3_client, class_account):
    contract, _ = web3_client.deploy_and_get_contract("./EIPs/MetaProxy", "0.8.10", account=class_account)
    return contract


@pytest.fixture(scope="class")
def event_caller_contract(web3_client, class_account) -> tp.Any:
    event_caller, _ = web3_client.deploy_and_get_contract("common/EventCaller", "0.8.12", class_account)
    yield event_caller


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
def wneon(web3_client, faucet, class_account):
    contract, _ = web3_client.deploy_and_get_contract(
        "common/WNeon", "0.4.26", account=class_account, contract_name="WNEON"
    )
    return contract


@pytest.fixture(scope="class")
def storage_contract(web3_client, class_account) -> tp.Any:
    contract, _ = web3_client.deploy_and_get_contract(
        "common/StorageSoliditySource",
        "0.8.8",
        class_account,
        contract_name="Storage",
        constructor_args=[],
    )
    yield contract


@pytest.fixture(scope="session")
def sol_price() -> float:
    """Get SOL price from Solana mainnet"""
    price = get_sol_price()
    with allure.step(f"SOL price {price}$"):
        return price


@pytest.fixture(scope="session")
def neon_price() -> float:
    """Get SOL price from Solana mainnet"""
    price = get_neon_price()
    with allure.step(f"NEON price {price}$"):
        return price
