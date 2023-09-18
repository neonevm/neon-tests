import json
import os
import pathlib
from collections import defaultdict

NETWORK_NAME = os.environ.get("NETWORK_NAME", "full_test_suite")
EXPANDED_ENVS = [
    "PROXY_URL",
    "NETWORK_ID",
    "FAUCET_URL",
    "SOLANA_URL",
]


class NetworkManager():
    def __init__(self):
        self.networks = {}

        with open(pathlib.Path.cwd() / "envs.json", "r") as f:
            self.networks = json.load(f)
            if NETWORK_NAME not in self.networks.keys() and os.environ.get("DUMP_ENVS"):
                environments = defaultdict(dict)
                for var in EXPANDED_ENVS:
                    environments[NETWORK_NAME].update({var.lower(): os.environ.get(var, "")})
                self.networks.update(environments)

    def get_network_param(self, network, param):
        value = ""
        if network in self.networks:
            value = self.networks[network][param]
        if isinstance(value, str):
            if os.environ.get("SOLANA_IP"):
                value = value.replace("<solana_ip>", os.environ.get("SOLANA_IP"))
            if os.environ.get("PROXY_IP"):
                value = value.replace("<proxy_ip>", os.environ.get("PROXY_IP"))
        return value
