import requests
from requests import Response
from solders.pubkey import Pubkey


class NeonApiRpcClient:
    def __init__(self, url: str, chain_id: int) -> None:
        self.url = url
        self.headers = {"Content-Type": "application/json"}
        self.chain_id = chain_id

    def post(self, method, params):
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": [params],
        }
        resp = requests.post(url=f"{self.url}", json=body, headers=self.headers).json()
        if "result" in resp:
            return resp["result"]
        return resp["error"]

    def get_storage_at(self, contract, index="0x0"):
        params = {"contract": contract, "index": index}
        return self.post("get_storage_at", params)

    def get_balance(self, ether: str, chain_id: str | None = None) -> Response:
        if not chain_id:
            chain_id = self.chain_id
        params = {"account": [{"address": ether, "chain_id": chain_id}]}
        return self.post("balance", params)

    def emulate(
        self, sender, contract, data=bytes(), chain_id: str | None = None, value="0x0", max_steps_to_execute=500000
    ) -> Response:
        if not chain_id:
            chain_id = self.chain_id

        if isinstance(data, bytes):
            data = data.hex()
        params = {
            "step_limit": max_steps_to_execute,
            "tx": {"from": sender, "to": contract, "data": data, "chain_id": chain_id, "value": value},
            "accounts": [],
        }
        return self.post("emulate", params)

    def get_contract(self, address) -> Response:
        params = {"contract": address}
        return self.post("contract", params)

    def get_holder(self, pubkey: Pubkey) -> Response:
        params = {"pubkey": str(pubkey)}
        return self.post("holder", params)

    def get_config(self) -> Response:
        params = {}
        return self.post("config", params)
