"""Script to deploy Curve contracts from: https://github.com/curvefi/curve-factory/blob/simple-dev/data.json"""
import os
import time
import random

import requests


FAUCET_URL = os.environ.get("FAUCET_URL")
PROXY_URL = os.environ.get("PROXY_URL")
NETWORK_ID = os.environ.get("NETWORK_ID")

CURVE_DATA_URL = (
    "https://raw.githubusercontent.com/curvefi/curve-factory/simple-dev/data.json"
)


curve_resp = requests.get(CURVE_DATA_URL)

if curve_resp.status_code != 200:
    raise Exception(f"Can't download Curve factory: {curve_resp.text}")

curve_data = curve_resp.json()

for tr in curve_data.values():
    resp = requests.post(
        f"{FAUCET_URL}/request_neon", json={"amount": 2000, "wallet": tr["origin"]}
    )
    assert resp.status_code == 200


for key in ["factory", "2", "3", "4"]:
    tr = curve_data[key]
    resp = requests.post(
        PROXY_URL,
        json={
            "jsonrpc": "2.0",
            "method": "eth_sendRawTransaction",
            "params": [tr["raw_tx"]],
            "id": random.randint(1, 1000),
        },
    )
    tr_id = resp.json()["value"]
    time.sleep(5)
    receipt = requests.post(
        PROXY_URL,
        json={
            "jsonrpc": "2.0",
            "method": "eth_getTransactionReceipt",
            "params": [tr_id],
            "id": random.randint(1, 1000),
        },
    ).json()

    assert receipt.status == 1, f"Transaction for factory: {key} failed: {receipt}"
