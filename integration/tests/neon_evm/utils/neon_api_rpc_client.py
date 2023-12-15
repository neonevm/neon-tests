import requests

from .constants import CHAIN_ID


class NeonApiRpcClient:
    def __init__(self, url):
        self.url = url
        self.headers = {"Content-Type": "application/json"}

    def post(self, method, params):
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": [params],
        }
        resp = requests.post(url=f"{self.url}", json=body, headers=self.headers).json()
        if "result" in resp:
            return resp['result']
        else:
            return resp['error']

    def get_storage_at(self, contract, index="0x0"):
        params = {"contract": contract, "index": index}
        return self.post("get_storage_at", params)

    def get_balance(self, ether, chain_id=CHAIN_ID):
        params = {"account": [{"address": ether, "chain_id": chain_id}]}

        return self.post("balance", params)

    def emulate(self, sender, contract, data=bytes(), chain_id=CHAIN_ID, value='0x0', max_steps_to_execute=500000):
        if isinstance(data, bytes):
            data = data.hex()
        params = {
            "step_limit": max_steps_to_execute,
            "tx": {
                "from": sender,
                "to": contract,
                "data": data,
                "chain_id": chain_id,
                "value": value
            },
            "accounts": []
        }
        return self.post("emulate", params)

    def get_contract(self, address):
        params = {"contract": address}
        return self.post("contract", params)

    def get_holder(self, pubkey):
        params = {"pubkey": str(pubkey)}
        return self.post("holder", params)