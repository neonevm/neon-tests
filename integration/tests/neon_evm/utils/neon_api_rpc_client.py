import eth_abi
from eth_utils import abi
from requests import Response, Session
from solders.pubkey import Pubkey


class NeonApiRpcClient:
    def __init__(self, url: str, chain_id: int) -> None:
        self.url = url
        self.chain_id = chain_id
        self.session = Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def _make_request(self, method, params):
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params if isinstance(params, list) else [params],
        }
        response = self.session.post(url=self.url, json=body)
        response.raise_for_status()

        resp_data = response.json()
        if "result" in resp_data:
            return resp_data["result"]

        return resp_data["error"]

    def get_storage_at(self, contract, index="0x0") -> Response:
        params = {"contract": contract, "index": index}
        return self._make_request("get_storage_at", params)

    def get_balance(self, ether: str, chain_id: str | None = None) -> Response:
        if not chain_id:
            chain_id = self.chain_id
        params = {"account": [{"address": ether, "chain_id": chain_id}]}
        return self._make_request("balance", params)

    def emulate(
        self,
        sender,
        contract,
        data=bytes(),
        chain_id: str | None = None,
        value="0x0",
        max_steps_to_execute=500000,
        provide_account_info=None,
        trace_config=None,
    ) -> Response:
        if not chain_id:
            chain_id = self.chain_id

        if isinstance(data, bytes):
            data = data.hex()
        params = {
            "step_limit": max_steps_to_execute,
            "tx": {"from": sender, "to": contract, "data": data, "chain_id": chain_id, "value": value},
            "accounts": [],
            "provide_account_info": provide_account_info,
            "trace_config": trace_config,
        }
        return self._make_request("emulate", params)

    def emulate_contract_call(
        self, sender, contract, function_signature, params=None, value=0, trace_config=None
    ) -> Response:

        data = abi.function_signature_to_4byte_selector(function_signature)
        if isinstance(value, int):
            value = hex(value)
        if params is not None:
            types = function_signature.split("(")[1].split(")")[0].split(",")
            data += eth_abi.encode(types, params)
        return self.emulate(sender, contract, data, value=value, trace_config=trace_config)

    def get_contract(self, address) -> Response:
        params = {"contract": address}
        return self._make_request("contract", params)

    def get_holder(self, pubkey: Pubkey) -> Response:
        params = {"pubkey": str(pubkey)}
        return self._make_request("holder", params)

    def get_config(self) -> Response:
        params = {}
        return self._make_request("config", params)
