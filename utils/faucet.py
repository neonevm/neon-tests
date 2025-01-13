import time

import requests
import typing as tp
import urllib.parse

from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client


class Faucet:
    def __init__(
        self,
        faucet_url: str,
        web3_client: NeonChainWeb3Client,
        session: tp.Optional[tp.Any] = None,
    ):
        self._url = faucet_url
        self._session = session or requests.Session()
        self.web3_client = web3_client

    def request_neon(self, address: str, amount: int = 100) -> requests.Response:
        assert address.startswith("0x"), "Invalid address format"
        url = urllib.parse.urljoin(self._url, "request_neon")
        balance_before = self.web3_client.get_balance(address)

        max_retries = 5
        retry_delay = 3  # seconds

        for attempt in range(max_retries):
            try:
                response = self._session.post(url, json={"amount": amount, "wallet": address})
                if "Blockhash not found" in response.text:
                    time.sleep(retry_delay)
                    continue
                response.raise_for_status()
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise RuntimeError(
                        "Failed to request neon after {} attempts: {}".format(max_retries, str(e))
                    )

        wait_condition(lambda: self.web3_client.get_balance(address) > balance_before)
        return response