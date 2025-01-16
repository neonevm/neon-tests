from typing import Optional
from datetime import date

import requests
from requests import RequestException
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import diskcache

from utils.logger import create_logger


logger = create_logger(__name__)
WAIT = 10
cache = diskcache.Cache("coingecko_cache")


class RateLimitError(Exception):
    pass


@retry(
    retry=retry_if_exception_type((RateLimitError, RequestException)),
    wait=wait_fixed(WAIT), stop=stop_after_attempt(15)
)
def get_coin_price(date_: date, coin_id: str, currency: str) -> Optional[float]:
    """
    https://docs.coingecko.com/reference/coins-id-history
    """
    cache_key = (date_, coin_id, currency)
    if cache_key in cache:
        return cache[cache_key]

    formatted_date = date_.strftime('%d-%m-%Y')
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/history?date={formatted_date}&localization=false'
    logger.info(f"Get {coin_id} price in {currency} on {date_}")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        try:
            price = data['market_data']['current_price'][currency]
            cache[cache_key] = price
            return price
        except KeyError:
            logger.error(f"No price data available for {formatted_date}.")
            return None

    elif response.status_code == 429:
        logger.warning(f"Rate limit hit. Retrying in {WAIT} seconds")
        raise RateLimitError()

    else:
        logger.error(f"Failed to retrieve data (Status Code: {response.status_code})")
        return None
