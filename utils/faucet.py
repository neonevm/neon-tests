import requests
import typing as tp
import urllib.parse
from busypie import wait_at_most, ONE_SECOND, TEN_SECONDS
from busypie.durations import TWO_MINUTES

from datetime import datetime

from http import HTTPStatus


class Faucet:
    def __init__(self, faucet_url: str, session: tp.Optional[tp.Any] = None):
        self._url = faucet_url
        self._session = session or requests.Session()

    def request_neon(self, address: str, amount: int = 100):
        assert address.startswith("0x")
        url = urllib.parse.urljoin(self._url, "request_neon")
        wait_at_most(TWO_MINUTES).poll_interval(TEN_SECONDS + ONE_SECOND).until(
            lambda: self.send_post_request(url, address, amount)
        )

    def send_post_request(self, url: str, address: str, amount: int) -> bool:
        response = self._session.post(url, json={"amount": amount, "wallet": address})
        return True if HTTPStatus.OK == response.status_code else False
