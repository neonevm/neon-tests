import urllib.parse
import requests


class Faucet:
    def __init__(self, faucet_url: str):
        self._url = faucet_url
        self._session = requests.Session()

    def request_neon(self, address: str, amount: int = 100):
        assert address.startswith("0x")
        url = urllib.parse.urljoin(self._url, "request_neon")
        resp = self._session.post(url, json={"amount": amount, "wallet": address})
        assert resp.status_code == 200
