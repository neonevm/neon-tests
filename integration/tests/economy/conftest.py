import asyncio

import allure
import pytest
from pythclient.pythaccounts import PythPriceAccount
from pythclient.solana import SolanaClient, SolanaPublicKey, SOLANA_MAINNET_HTTP_ENDPOINT


@pytest.fixture(scope="session")
def sol_price() -> float:
    async def get_price():
        account_key = SolanaPublicKey("H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG")
        solana_client = SolanaClient(endpoint=SOLANA_MAINNET_HTTP_ENDPOINT)
        price: PythPriceAccount = PythPriceAccount(account_key, solana_client)
        await price.update()
        return price.aggregate_price

    loop = asyncio.get_event_loop()
    price = loop.run_until_complete(get_price())
    with allure.step(f"SOL price {price}$"):
        return price
