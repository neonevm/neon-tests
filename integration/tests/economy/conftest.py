import asyncio

import allure
import pytest
from pythclient.pythaccounts import PythPriceAccount
from pythclient.solana import SolanaClient, SolanaPublicKey, SOLANA_MAINNET_HTTP_ENDPOINT
from _pytest.config import Config


def get_sol_price() -> float:
    """Get SOL price from Solana mainnet"""
    async def get_price():
        account_key = SolanaPublicKey("H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG")
        solana_client = SolanaClient(endpoint=SOLANA_MAINNET_HTTP_ENDPOINT)
        price: PythPriceAccount = PythPriceAccount(account_key, solana_client)
        await price.update()
        return price.aggregate_price

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(get_price())


@pytest.fixture(scope="session")
def sol_price() -> float:
    """Get SOL price from Solana mainnet"""
    price = get_sol_price()
    with allure.step(f"SOL price {price}$"):
        return price


@pytest.fixture(scope="function")
def sol_client_tx_v2(pytestconfig: Config):
    """Client for work with transactions version 2"""
    client = SolanaClient(endpoint=pytestconfig.environment.solana_url)
    return client
