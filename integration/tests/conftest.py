import pathlib
import random
import shutil
import string

import allure
import pytest
import solana
import solana.rpc.api
from _pytest.config import Config
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.instructions import create_associated_token_account, get_associated_token_address

from integration.tests.basic.helpers.basic import BaseMixin
from utils.erc20wrapper import ERC20Wrapper
from utils.erc721ForMetaplex import ERC721ForMetaplex
from utils.faucet import Faucet
from utils.operator import Operator
from utils.web3client import NeonWeb3Client
from utils.apiclient import JsonRPCSession

LAMPORT_PER_SOL = 1_000_000_000
NEON_AIRDROP_AMOUNT = 10_000


def pytest_addoption(parser):
    parser.addoption("--network", action="store", default="night-stand", help="Which stand use")


def pytest_collection_modifyitems(config, items):
    deselected_items = []
    selected_items = []
    if config.getoption("--network") == 'devnet':
        deselected_mark = 'only_stands'
    else:
        deselected_mark = 'only_devnet'

    for item in items:
        if item.get_closest_marker(deselected_mark):
            deselected_items.append(item)
        else:
            selected_items.append(item)

    config.hook.pytest_deselected(items=deselected_items)
    items[:] = selected_items


@pytest.fixture(scope="session", autouse=True)
def faucet(pytestconfig: Config) -> Faucet:
    return Faucet(pytestconfig.environment.faucet_url)


@pytest.fixture(scope="session")
def json_rpc_client(pytestconfig: Config) -> JsonRPCSession:
    return JsonRPCSession(pytestconfig.environment.proxy_url)


@pytest.fixture(scope="session", autouse=True)
def web3_client(pytestconfig: Config) -> NeonWeb3Client:
    client = NeonWeb3Client(pytestconfig.environment.proxy_url, pytestconfig.environment.network_id)
    return client


@pytest.fixture(scope="session", autouse=True)
def sol_client(pytestconfig: Config):
    client = solana.rpc.api.Client(pytestconfig.environment.solana_url)
    return client


@pytest.fixture(scope="session", autouse=True)
def operator(pytestconfig: Config, web3_client: NeonWeb3Client) -> Operator:
    return Operator(
        pytestconfig.environment.proxy_url,
        pytestconfig.environment.solana_url,
        pytestconfig.environment.network_id,
        pytestconfig.environment.operator_neon_rewards_address,
        pytestconfig.environment.spl_neon_mint,
        pytestconfig.environment.operator_keys,
        web3_client=web3_client,
    )


@pytest.fixture(scope="session", autouse=True)
def allure_environment(pytestconfig: Config, web3_client: NeonWeb3Client):
    opts = {
        "Proxy.Version": web3_client.get_proxy_version()["result"],
        "EVM.Version": web3_client.get_evm_version()["result"],
        "CLI.Version": web3_client.get_cli_version()["result"],
    }

    allure_path = pytestconfig.getoption("--alluredir")

    yield opts
    with open(pathlib.Path() / allure_path / "environment.properties", "w+") as f:
        f.write("\n".join(map(lambda x: f"{x[0]}={x[1]}", opts.items())))
        f.write("\n")
    categories_from = pathlib.Path() / "allure" / "categories.json"
    categories_to = pathlib.Path() / allure_path / "categories.json"
    shutil.copy(categories_from, categories_to)


@pytest.fixture(scope="class")
def prepare_account(operator, faucet, web3_client: NeonWeb3Client):
    """Create new account for tests and save operator pre/post balances"""
    with allure.step("Create account for tests"):
        acc = web3_client.eth.account.create()
    with allure.step(f"Request {NEON_AIRDROP_AMOUNT} NEON from faucet for {acc.address}"):
        faucet.request_neon(acc.address, NEON_AIRDROP_AMOUNT)
        assert web3_client.get_balance(acc) == NEON_AIRDROP_AMOUNT
    start_neon_balance = operator.get_neon_balance()
    start_sol_balance = operator.get_solana_balance()
    with allure.step(
            f"Operator initial balance: {start_neon_balance / LAMPORT_PER_SOL} NEON {start_sol_balance / LAMPORT_PER_SOL} SOL"
    ):
        pass
    yield acc
    end_neon_balance = operator.get_neon_balance()
    end_sol_balance = operator.get_solana_balance()
    with allure.step(
            f"Operator end balance: {end_neon_balance / LAMPORT_PER_SOL} NEON {end_sol_balance / LAMPORT_PER_SOL} SOL"
    ):
        pass
    with allure.step(f"Account end balance: {web3_client.get_balance(acc)} NEON"):
        pass


@pytest.fixture(scope="session")
def erc20_spl(web3_client: NeonWeb3Client, faucet, pytestconfig: Config, sol_client):
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(web3_client, faucet, f"Test {symbol}", symbol, sol_client, mintable=False,
                         evm_loader_id=pytestconfig.environment.evm_loader)
    erc20.claim(erc20.account, bytes(erc20.solana_associated_token_acc), 100000000000000)
    yield erc20


@pytest.fixture(scope="session")
def erc20_spl_mintable(web3_client: NeonWeb3Client, faucet, sol_client):
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(web3_client, faucet, f"Test {symbol}", symbol, sol_client, mintable=True)
    erc20.mint_tokens(erc20.account, erc20.account.address)
    yield erc20


@pytest.fixture(scope="function")
def solana_associated_token_mintable_erc20(erc20_spl_mintable, sol_client):
    acc = Keypair.generate()
    sol_client.request_airdrop(acc.public_key, 1000000000)
    BaseMixin.wait_condition(lambda: sol_client.get_balance(acc.public_key)["result"]["value"] == 1000000000)
    token_mint = PublicKey(erc20_spl_mintable.contract.functions.tokenMint().call())
    trx = Transaction()
    trx.add(create_associated_token_account(acc.public_key, acc.public_key, token_mint))
    opts = TxOpts(skip_preflight=True, skip_confirmation=False)
    sol_client.send_transaction(trx, acc, opts=opts)
    solana_address = bytes(get_associated_token_address(acc.public_key, token_mint))
    yield acc, token_mint, solana_address

@pytest.fixture(scope="function")
def solana_associated_token_erc20(erc20_spl, sol_client):
    acc = Keypair.generate()
    sol_client.request_airdrop(acc.public_key, 1000000000)
    BaseMixin.wait_condition(lambda: sol_client.get_balance(acc.public_key)["result"]["value"] == 1000000000)
    token_mint = erc20_spl.token_mint.pubkey
    trx = Transaction()
    trx.add(create_associated_token_account(acc.public_key, acc.public_key, token_mint))
    opts = TxOpts(skip_preflight=True, skip_confirmation=False)
    sol_client.send_transaction(trx, acc, opts=opts)
    solana_address = bytes(get_associated_token_address(acc.public_key, token_mint))
    yield acc, token_mint, solana_address


@pytest.fixture(scope="class")
def multiple_actions_erc20(web3_client, faucet):
    acc = web3_client.create_account()
    faucet.request_neon(acc.address, 100)
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])

    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "multiple_actions_erc20", "0.8.10", acc, contract_name="multipleActionsERC20",
        constructor_args=[f"Test {symbol}", symbol, 18]
    )
    return acc, contract


@pytest.fixture(scope="class")
def erc721(web3_client: NeonWeb3Client, faucet, pytestconfig: Config):
    contract = ERC721ForMetaplex(web3_client, faucet)
    return contract


@pytest.fixture(scope="class")
def nft_receiver(web3_client, faucet):
    acc = web3_client.create_account()
    faucet.request_neon(acc.address, 100)
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "erc721_receiver", "0.8.10", acc, contract_name="ERC721Receiver")
    return contract


@pytest.fixture(scope="class")
def invalid_nft_receiver(web3_client, faucet):
    acc = web3_client.create_account()
    faucet.request_neon(acc.address, 100)
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "erc721_invalid_receiver", "0.8.10", acc, contract_name="ERC721Receiver")
    return contract


@pytest.fixture(scope="class")
def multiple_actions_erc721(web3_client, faucet):
    acc = web3_client.create_account()
    faucet.request_neon(acc.address)
    contract, contract_deploy_tx = web3_client.deploy_and_get_contract(
        "multiple_actions_erc721", "0.8.10", acc, contract_name="multipleActionsERC721"
    )
    return acc, contract


@pytest.fixture(scope="function")
def new_account(web3_client, faucet):
    new_acc = web3_client.create_account()
    faucet.request_neon(new_acc.address, 100)
    yield new_acc
