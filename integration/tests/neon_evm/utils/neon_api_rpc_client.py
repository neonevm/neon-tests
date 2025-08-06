import json

import allure
import eth_abi
from eth_utils import abi
from requests import Session
from solders.pubkey import Pubkey

from utils.logger import log_text_to_allure_and_stdout
from utils.models.tree_account import TreeAccount
from utils.types import Caller, Contract


class NeonApiRpcClient:
    def __init__(self, url: str, chain_id: int, sol_chain_id: int) -> None:
        self.url = url
        self.chain_id = chain_id
        self.sol_chain_id = sol_chain_id
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
        log_text_to_allure_and_stdout("Making request to Neon API", str(body))
        response = self.session.post(url=self.url, json=body)
        response.raise_for_status()

        resp_data = response.json()
        log_text_to_allure_and_stdout("Response from Neon API", str(resp_data))

        if "result" in resp_data:
            return resp_data["result"]

        return resp_data["error"]

    def get_storage_at(self, contract, index="0x0") -> json:
        params = {"contract": contract, "index": index}
        return self._make_request("get_storage_at", params)

    def get_balance(self, ether: str, chain_id: str | None = None) -> json:
        if not chain_id:
            chain_id = self.chain_id
        params = {"account": [{"address": ether, "chain_id": chain_id}]}
        return self._make_request("balance", params)[0]

    @allure.step("Emulate transaction")
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
    ) -> json:
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

    @allure.step("Emulate contract call")
    def emulate_contract_call(
        self, sender, contract, function_signature, params=None, value=0, trace_config=None
    ) -> json:

        data = abi.function_signature_to_4byte_selector(function_signature)
        if isinstance(value, int):
            value = hex(value)
        if params is not None:
            types = function_signature.split("(")[1].split(")")[0].split(",")
            data += eth_abi.encode(types, params)
        return self.emulate(sender, contract, data, value=value, trace_config=trace_config)

    @allure.step("Emulate transaction from holder account")
    def emulate_from_holder(self, holder_pubkey: Pubkey, max_steps_to_execute=500000):
        params = {"step_limit": max_steps_to_execute, "holder_pubkey": str(holder_pubkey)}
        return self._make_request("emulate_from_holder", params)

    def get_additional_accounts_by_emulation(
        self, sender, contract, function_signature, params=None, value=0, trace_config=None
    ):
        result = self.emulate_contract_call(sender, contract, function_signature, params, value, trace_config)
        if "solana_accounts" in result:
            return [Pubkey.from_string(item["pubkey"]) for item in result["solana_accounts"]]
        else:
            raise ValueError(f"Emulation failed: {result}")

    def get_contract(self, address) -> json:
        params = {"contract": address}
        return self._make_request("contract", params)[0]

    def get_holder(self, pubkey: Pubkey) -> json:
        params = {"pubkey": str(pubkey)}
        return self._make_request("holder", params)

    def get_config(self) -> json:
        params = {}
        return self._make_request("config", params)

    @allure.step("Simulate Solana transaction")
    def simulate_solana(self, blockhash: str, transactions: list[str], solana_overrides_params=None) -> json:
        params = {
            "blockhash": blockhash,
            "transactions": transactions,
            "solana_overrides": solana_overrides_params,
        }
        return self._make_request("simulate_solana", params)

    def call_contract_get_function(self, sender, contract, function_signature: str, args=None):
        data = abi.function_signature_to_4byte_selector(function_signature)
        if args is not None:
            data += args
        result = self.emulate(sender.eth_address.hex(), contract.eth_address.hex(), data)
        return result["result"]

    def get_steps_count(self, from_acc, to, data) -> int:
        if isinstance(to, (Caller, Contract)):
            to = to.eth_address.hex()
        result = self.emulate(from_acc.eth_address.hex(), to, data)
        return result["steps_executed"]

    def get_transaction_tree(self, address, nonce, chain_id: int | None = None) -> TreeAccount:
        if not chain_id:
            chain_id = self.sol_chain_id

        if isinstance(address, Pubkey):
            address = bytes(address).hex()
        params = {"origin": {"address": address, "chain_id": chain_id}, "nonce": nonce}
        response = self._make_request("transaction_tree", params)
        return TreeAccount.from_dict(response)

    def get_container_accounts(self, pubkey: Pubkey) -> json:
        params = {"pubkey": str(pubkey)}
        return self._make_request("container", params)["accounts"]

    def get_account_data_from_container(self, container_pubkey: Pubkey, account_pubkey: Pubkey) -> bytes | None:
        all_accounts = self.get_container_accounts(container_pubkey)
        for account in all_accounts:
            if account["pubkey"] == str(account_pubkey):
                return bytes.fromhex(account["data"])
        return None
