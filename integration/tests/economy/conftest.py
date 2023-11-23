import allure
import pytest

from pythclient.solana import SolanaClient
from _pytest.config import Config

from integration.tests.basic.helpers.chains import make_nonce_the_biggest_for_chain
from utils.erc20wrapper import ERC20Wrapper
from utils.prices import get_sol_price, get_neon_price


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


@pytest.fixture(scope="session")
def sol_client_tx_v2(pytestconfig: Config):
    """Client for work with transactions version 2"""
    client = SolanaClient(
        pytestconfig.environment.solana_url,
        pytestconfig.environment.account_seed_version,
    )
    return client


# @pytest.fixture(scope="class")
# def temp_acc(web3_client):
#     key = "0x931babf4129096d628e0d5e642bd5768fd1bcfb79c6f5b95ffa471c350da4207"
#     return web3_client.eth.account.from_key(key)


@pytest.fixture(scope="class")
def counter_contract(account_with_all_tokens, client_and_price, web3_client_sol, web3_client):
    w3_client, _ = client_and_price
    make_nonce_the_biggest_for_chain(account_with_all_tokens, w3_client, [web3_client, web3_client_sol])
    contract, _ = w3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=account_with_all_tokens)
    return contract


@pytest.fixture(scope="class", params=["neon", "sol"])
def client_and_price(web3_client, web3_client_sol, sol_price, neon_price, request, pytestconfig):
    if request.param == "neon":
        return web3_client, neon_price
    elif request.param == "sol":
        if "sol" in pytestconfig.environment.network_ids:
            return web3_client_sol, sol_price
    pytest.skip(f"{request.param} chain is not available")


@pytest.fixture(scope="class")
def erc20_wrapper(
    erc20_spl_mintable,
    account_with_all_tokens,
    client_and_price,
    faucet,
    solana_account,
    sol_client,
    web3_client_sol,
    web3_client,
):
    client, _ = client_and_price
    make_nonce_the_biggest_for_chain(account_with_all_tokens, client, [web3_client, web3_client_sol])
    contract = ERC20Wrapper(
        client,
        faucet,
        "Test AAA",
        "AAA",
        sol_client,
        account=account_with_all_tokens,
        solana_account=solana_account,
        mintable=True,
    )
    contract.mint_tokens(account_with_all_tokens, contract.account.address)
    return contract

