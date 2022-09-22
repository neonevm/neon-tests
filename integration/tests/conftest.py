import pathlib
import random
import shutil
import string

import allure
import pytest
import solana
import solana.rpc.api
import solcx
from _pytest.config import Config
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from spl.token.instructions import create_associated_token_account, get_associated_token_address

from integration.tests.basic.helpers.basic import BaseMixin
from utils.erc20wrapper import ERC20Wrapper
from utils.faucet import Faucet
from utils.operator import Operator
from utils.web3client import NeonWeb3Client
from utils.apiclient import JsonRPCSession

LAMPORT_PER_SOL = 1_000_000_000
NEON_AIRDROP_AMOUNT = 10_000


def pytest_addoption(parser):
    parser.addoption("--network", action="store", default="night-stand", help="Which stand use")


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
def erc20wrapper(web3_client: NeonWeb3Client, faucet, pytestconfig: Config):
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    erc20 = ERC20Wrapper(web3_client, faucet, name=f"Test {symbol}", symbol=symbol)
    erc20.mint_tokens(erc20.account, erc20.account.address)
    yield erc20


@pytest.fixture(scope="function")
def solana_acc(erc20wrapper, sol_client):
    acc = Keypair.generate()
    sol_client.request_airdrop(acc.public_key, 1000000000)
    BaseMixin.wait_condition(lambda: sol_client.get_balance(acc.public_key)["result"]["value"] == 1000000000)
    token_mint = PublicKey(erc20wrapper.contract.functions.tokenMint().call())
    trx = Transaction()
    trx.add(create_associated_token_account(acc.public_key, acc.public_key, token_mint))
    opts = TxOpts(skip_preflight=True, skip_confirmation=False)
    sol_client.send_transaction(trx, acc, opts=opts)
    solana_address = bytes(get_associated_token_address(acc.public_key, token_mint))
    yield acc, token_mint, solana_address


@pytest.fixture(scope="function")
def multiply_actions_erc20(web3_client, faucet):
    acc = web3_client.create_account()
    faucet.request_neon(acc.address, 100)
    contract_path = (
            pathlib.Path.cwd() / "contracts" / "multiply_actions_erc20.sol"
    ).absolute()

    with open(contract_path, "r") as s:
        source = s.read()
    compiled = solcx.compile_source(source, output_values=["abi", "bin"], solc_version="0.8.10",
                                    base_path=pathlib.Path.cwd() / "contracts", optimize=True)
    contract_interface = compiled['<stdin>:multiplyActionsERC20']
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])

    contract_deploy_tx = web3_client.deploy_contract(acc, abi=contract_interface["abi"],
                                                     bytecode=contract_interface["bin"],
                                                     constructor_args=[f"Test {symbol}", symbol, 18]
                                                     )
    contract = web3_client.eth.contract(address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"])
    return acc, contract
