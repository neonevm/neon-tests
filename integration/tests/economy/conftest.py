import allure
import pytest

from pythclient.solana import SolanaClient
from _pytest.config import Config

from utils.helpers import get_sol_price


@pytest.fixture(scope="session")
def sol_price() -> float:
    """Get SOL price from Solana mainnet"""
    price = get_sol_price()
    with allure.step(f"SOL price {price}$"):
        return price


@pytest.fixture(scope="session")
def sol_client_tx_v2(pytestconfig: Config):
    """Client for work with transactions version 2"""
    client = SolanaClient(pytestconfig.environment.solana_url, pytestconfig.environment.account_seed_version)
    return client
