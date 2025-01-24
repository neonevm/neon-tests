from typing import Dict

import eth_abi
import requests
from eth_utils import abi
from solders.pubkey import Pubkey

from utils.models.tree_account import TreeAccount
from utils.types import Caller, Contract


class NeonApiClient:
    def __init__(self, url: str, chain_id: int, sol_chain_id: int) -> None:
        self.url = url
        self.headers = {"Content-Type": "application/json"}
        self.chain_id = chain_id
        self.sol_chain_id = sol_chain_id

    def emulate(
        self,
        sender,
        contract,
        data=bytes(),
        chain_id: int | None = None,
        value="0x0",
        max_steps_to_execute=500000,
        provide_account_info=None,
        trace_config=None,
    ):
        chain_id = chain_id or self.chain_id

        if isinstance(data, bytes):
            data = data.hex()
        body = {
            "step_limit": max_steps_to_execute,
            "tx": {"from": sender, "to": contract, "data": data, "chain_id": chain_id, "value": value},
            "accounts": [],
            "provide_account_info": provide_account_info,
            "trace_config": trace_config,
        }
        resp = requests.post(url=f"{self.url}/emulate", json=body, headers=self.headers)
        if resp.status_code == 200:
            return resp.json()["value"]
        else:
            return resp.json()

    def emulate_contract_call(self, sender, contract, function_signature, params=None, value="0x0", trace_config=None):
        # does not work for tuple in params
        data = abi.function_signature_to_4byte_selector(function_signature)

        if params is not None:
            types = function_signature.split("(")[1].split(")")[0].split(",")
            data += eth_abi.encode(types, params)
        return self.emulate(sender, contract, data, value=value, trace_config=trace_config)

    def get_storage_at(self, contract_id, index="0x0") -> Dict:
        body = {"contract": contract_id, "index": index}
        return requests.post(url=f"{self.url}/storage", json=body, headers=self.headers).json()

    def get_holder(self, public_key) -> Dict:
        body = {"pubkey": f"{public_key}"}
        return requests.post(url=f"{self.url}/holder", json=body, headers=self.headers).json()

    def get_balance(self, ether, chain_id: int | None = None) -> Dict:
        if not chain_id:
            chain_id = self.chain_id

        body = {"account": [{"address": ether, "chain_id": chain_id}]}
        return requests.post(url=f"{self.url}/balance", json=body, headers=self.headers).json()

    def call_contract_get_function(self, sender, contract, function_signature: str, args=None):
        data = abi.function_signature_to_4byte_selector(function_signature)
        if args is not None:
            data += args
        result = self.emulate(sender.eth_address.hex(), contract.eth_address.hex(), data)
        return result["result"]

    def get_steps_count(self, from_acc, to, data):
        if isinstance(to, (Caller, Contract)):
            to = to.eth_address.hex()
        result = self.emulate(from_acc.eth_address.hex(), to, data)
        return result["steps_executed"]

    def get_transaction_tree(self, address, nonce, chain_id: int | None = None) -> TreeAccount:
        if not chain_id:
            chain_id = self.sol_chain_id

        if isinstance(address, Pubkey):
            address = bytes(address).hex()
        body = {"origin": {"address": address, "chain_id": chain_id}, "nonce": nonce}
        response = requests.post(url=f"{self.url}/transaction_tree", json=body, headers=self.headers).json()
        return TreeAccount.from_dict(response)
