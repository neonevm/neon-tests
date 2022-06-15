import time
import requests
import typing as tp
import urllib.parse
from busypie import FIVE_SECONDS, wait_at_most
from busypie.durations import TWO_MINUTES
from http import HTTPStatus


class Faucet:
    def __init__(self, faucet_url: str, session: tp.Optional[tp.Any] = None):
        self._url = faucet_url
        self._session = session or requests.Session()

    def request_neon(self, address: str, amount: int = 100) -> requests.Response:
        assert address.startswith("0x")
        url = urllib.parse.urljoin(self._url, "request_neon")
        result = wait_at_most(TWO_MINUTES).poll_interval(FIVE_SECONDS).until(
            lambda: self.send_post_request(url, address, amount)
        )
        # needed for devnet
        time.sleep(1)
        return result

    def send_post_request(self, url: str, address: str, amount: int) -> bool:
        response = self._session.post(url, json={"amount": amount, "wallet": address})
        return response if HTTPStatus.OK == response.status_code else False
