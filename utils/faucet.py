import requests
import typing as tp
import urllib.parse


class Faucet:
    def __init__(self, faucet_url: str, session: tp.Optional[tp.Any] = None):
        self._url = faucet_url
        self._session = session or requests.Session()

    def request_neon(self, address: str, amount: int = 100):
        assert address.startswith("0x")
        url = urllib.parse.urljoin(self._url, "request_neon")
        response = self._session.post(url, json={"amount": amount, "wallet": address})
        assert response.ok, "Faucet returned error: {}".format(response.text)
        return response
