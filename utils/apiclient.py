import json
import random
import time
import typing as tp

import allure
from requests import Session


class JsonRPCSession(Session):
    def __init__(self, url):
        super(JsonRPCSession, self).__init__()
        self.url = url

    @allure.step("Send rpc request")
    def send_rpc(
        self,
        method: str,
        params: tp.Optional[tp.Any] = None,
        req_type: tp.Optional[str] = None,
    ) -> tp.Dict:
        req_id = random.randint(0, 100)
        body = {"jsonrpc": "2.0", "method": method, "id": req_id}

        if req_type is not None:
            body["req_type"] = req_type

        if params:
            if not isinstance(params, (list, tuple)):
                params = [params]
            body["params"] = params

        resp = self.post(self.url, json=body, timeout=60)
        response_body = resp.json()
        if "result" not in response_body and "error" not in response_body:
            raise AssertionError("Request must contains 'result' or 'error' field")

        if "error" in response_body:
            assert "result" not in response_body, "Response can't contains error and result"
        if "error" not in response_body:
            assert response_body["id"] == req_id
        allure.attach(json.dumps(response_body, indent=2), name="response", attachment_type=allure.attachment_type.JSON)
        return response_body

    def get_contract_code(self, contract_address: str) -> str:
        response = self.send_rpc("eth_getCode", [contract_address, "latest"])
        return response["result"]

    def get_neon_trx_receipt(self, trx_hash: str) -> tp.Dict:
        return self.send_rpc("neon_getTransactionReceipt", params=[trx_hash])

    def get_solana_trx_by_neon(self, trx_hash: str) -> tp.Dict:
        return self.send_rpc("neon_getSolanaTransactionByNeonTransaction", params=[trx_hash])

    def get_neon_gas_price(self) -> tp.Dict:
        return self.send_rpc("neon_gasPrice", params=[])

    def get_neon_pending_transactions(self, user_address):
        return self.send_rpc("neon_getPendingTransactions", params=[user_address])

    def get_neon_estimate_scheduled_gas(self, params):
        return self.send_rpc("neon_estimateScheduledGas", params=[params])

    def get_neon_estimate_gas(self, raw_tx, params):
        return self.send_rpc("neon_estimateGas", params=[raw_tx, params])

    def get_neon_emulate(self, params):
        return self.send_rpc("neon_emulate", params=[params])

    def send_neon_scheduled_transaction(self, trx_hash) -> tp.Dict:
        return self.send_rpc("neon_sendRawScheduledTransaction", params=[trx_hash])

    def wait_finalized_block(self, block_num: int):
        fin_block_num = block_num - 32
        while block_num > fin_block_num:
            time.sleep(1)
            response = self.send_rpc("neon_finalizedBlockNumber", [])
            fin_block_num = int(response["result"], 16)
