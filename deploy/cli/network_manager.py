import json
import os
import pathlib
from collections import defaultdict

NETWORK_NAME = os.environ.get("NETWORK", "full_test_suite")
EXPANDED_ENVS = [
    "PROXY_URL",
    "FAUCET_URL",
    "SOLANA_URL",
]


class NetworkManager:
    def __init__(self, network_name=NETWORK_NAME):
        self._networks = {}
        self.network_name = network_name

        with open(pathlib.Path.cwd() / "envs.json", "r") as f:
            self._networks = json.load(f)
            environments = defaultdict(dict)

            if self.network_name not in self._networks.keys() and os.environ.get("DUMP_ENVS"):
                for var in EXPANDED_ENVS:
                    environments[self.network_name].update({var.lower(): os.environ.get(var, "")})
                environments[self.network_name]["network_ids"] = {"neon": os.environ.get("NETWORK_ID", "")}
                self._networks.update(environments)

            if self.network_name in ["devnet", "tracer_ci"]:
                if "DEVNET_FAUCET_URL" in os.environ and os.environ["DEVNET_FAUCET_URL"]:
                    self._networks[self.network_name]["faucet_url"] = os.environ.get("DEVNET_FAUCET_URL")
                else:
                    raise RuntimeError("DEVNET_FAUCET_URL is not set")
                if "DEVNET_SOLANA_URL" in os.environ and os.environ["DEVNET_SOLANA_URL"]:
                    self._networks[self.network_name]["solana_url"] = os.environ.get("DEVNET_SOLANA_URL")
                else:
                    raise RuntimeError("DEVNET_SOLANA_URL is not set")


    def get_network_param(self, network, params=None):
        value = ""
        if network in self._networks:
            value = self._networks[network]

            if params:
                for item in params.split("."):
                    value = value[item]
        if isinstance(value, str):
            if os.environ.get("SOLANA_IP"):
                value = value.replace("<solana_ip>", os.environ.get("SOLANA_IP"))
            if os.environ.get("PROXY_IP"):
                value = value.replace("<proxy_ip>", os.environ.get("PROXY_IP"))
        return value

    def get_network_object(self, network_name):
        network = self.get_network_param(network_name)
        if network_name == "terraform":
            network["proxy_url"] = self.get_network_param(network_name, "proxy_url")
            network["solana_url"] = self.get_network_param(network_name, "solana_url")
            network["faucet_url"] = self.get_network_param(network_name, "faucet_url")

        return network
