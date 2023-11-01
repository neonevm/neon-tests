import requests
import typing as tp
import urllib.parse

from utils.helpers import wait_condition
from utils.web3client import NeonChainWeb3Client


class Faucet:
    def __init__(self, faucet_url: str, web3_client: NeonChainWeb3Client, session: tp.Optional[tp.Any] = None):
        self._url = faucet_url
        self._session = session or requests.Session()
        self.web3_client = web3_client

    def request_neon(self, address: str, amount: int = 100) -> requests.Response:
        assert address.startswith("0x")
        url = urllib.parse.urljoin(self._url, "request_neon")
        balance_before = self.web3_client.get_balance(address)
        response = self._session.post(url, json={"amount": amount, "wallet": address})
        assert response.ok, "Faucet returned error: {}, status code: {}, url: {}".format(response.text,
                                                                                         response.status_code,
                                                                                         response.url)
        wait_condition(lambda: self.web3_client.get_balance(address) > balance_before)
        return response
