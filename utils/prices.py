import asyncio
import pathlib
import logging
import time

from pythclient.pythaccounts import PythPriceAccount
from pythclient.solana import (
    SolanaClient,
    SolanaPublicKey,
    SOLANA_MAINNET_HTTP_ENDPOINT,
    SOLANA_DEVNET_HTTP_ENDPOINT,
    SOLANA_TESTNET_HTTP_ENDPOINT,
)

LOG = logging.getLogger(__name__)

SOL_FEED_ADDRESSES = {
    "mainnet": {
        "feed_address": "H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG",
        "solana_address": SOLANA_MAINNET_HTTP_ENDPOINT,
    },
    "testnet": {
        "feed_address": "7VJsBtJzgTftYzEeooSDYyjKXvYRWJHdwvbwfBvTg9K",
        "solana_address": SOLANA_TESTNET_HTTP_ENDPOINT,
    },
    "devnet": {
        "feed_address": "J83w4HKfqxwcq3BEMMkPFSppX3gqekLyLJBexebFVkix",
        "solana_address": SOLANA_DEVNET_HTTP_ENDPOINT,
    },
}

NEON_FEED_ADDRESSES = {
    "devnet": {
        "feed_address": "CkHTGkLkTLcb4dASq5qWshwGqnJz9YQWCQ3qac6G24Rt",
        "solana_address": SOLANA_DEVNET_HTTP_ENDPOINT,
    },
}

BTC_FEED_ADDRESSES = {
    "devnet": {
        "feed_address": "HovQMDrbAgAYPCmHVSrezcSmkMtXSSUsLDFANExrZh2J",
        "solana_address": SOLANA_DEVNET_HTTP_ENDPOINT,
    }
}


async def get_price(solana_address: str, feed_address: str):
    account_key = SolanaPublicKey(feed_address)
    solana_client = SolanaClient(endpoint=solana_address)
    price: PythPriceAccount = PythPriceAccount(account_key, solana_client)
    try:
        await price.update()
    except Exception as e:
        LOG.warning(f"Can't get price from Pyth network '{solana_address}' {e}")
    else:
        return price
    finally:
        await solana_client.close()


def get_sol_price() -> float:
    """Get SOL price from Solana mainnet"""
    for network in SOL_FEED_ADDRESSES:
        try:
            result = asyncio.run(
                get_price(
                    SOL_FEED_ADDRESSES[network]["solana_address"],
                    SOL_FEED_ADDRESSES[network]["feed_address"],
                )
            ).aggregate_price
            break
        except Exception as e:
            LOG.warning(f"Get error when try to get SOL price from: {network}: {e}")
            time.sleep(5)
    else:
        raise AssertionError("Can't get SOL price for all networks")
    return result


def get_neon_price() -> float:
    for network in NEON_FEED_ADDRESSES:
        try:
            result = asyncio.run(
                get_price(
                    NEON_FEED_ADDRESSES[network]["solana_address"],
                    NEON_FEED_ADDRESSES[network]["feed_address"],
                )
            ).aggregate_price
            break
        except Exception as e:
            LOG.warning(f"Get error when try to get NEON price from: {network}: {e}")
            time.sleep(5)
    else:
        raise AssertionError("Can't get NEON price for all networks")
    return result


def get_btc_price_detailed() -> PythPriceAccount:
    for network in BTC_FEED_ADDRESSES:
        try:
            result = asyncio.run(
                get_price(
                    BTC_FEED_ADDRESSES[network]["solana_address"],
                    BTC_FEED_ADDRESSES[network]["feed_address"],
                )
            )
            break
        except Exception as e:
            LOG.warning(f"Get error when try to get BTC price from: {network}: {e}")
            time.sleep(5)
    else:
        raise AssertionError("Can't get BTC price for all networks")
    return result
