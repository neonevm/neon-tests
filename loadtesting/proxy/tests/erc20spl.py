import random
import string
import logging
import time

import web3
from locust import tag, task, User, events

from utils.web3client import NeonWeb3Client
from utils.faucet import Faucet
from utils.erc20wrapper import ERC20Wrapper

from loadtesting.proxy.common.base import NeonProxyTasksSet

LOG = logging.getLogger(__name__)

ERC20SPL_CONTRACT_NAME = "erc20_for_spl_factory.sol"
ERC20SPL_CONTRACT_VERSION = "0.8.10"


@events.test_start.add_listener
def prepare_one_contract_for_erc20(environment: "locust.env.Environment", **kwargs):
    if environment.parsed_options.exclude_tags and "erc20spl" in environment.parsed_options.exclude_tags:
        return
    if environment.parsed_options.tags and "erc20spl" not in environment.parsed_options.tags:
        return

    neon_client = NeonWeb3Client(environment.credentials["proxy_url"], environment.credentials["network_id"])
    faucet = Faucet(environment.credentials["faucet_url"], neon_client)

    eth_account = neon_client.create_account()
    faucet.request_neon(eth_account.address, 10000)

    LOG.info("Deploy ERC20 contract for erc20spl test")
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    name = f"Test {symbol}"

    erc20_wrapper = ERC20Wrapper(neon_client, faucet, name, symbol, None, account=eth_account, mintable=True)
    erc20_wrapper.deploy_wrapper(True)
    erc20_wrapper.mint_tokens(eth_account, eth_account.address, 18446744073709551615)

    environment.erc20_one = {
        "user": eth_account,
        "contract": erc20_wrapper.get_wrapper_contract()
    }


@tag("erc20spl")
class ERC20SPLTasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    def on_start(self) -> None:
        super().on_start()
        contract = self.user.environment.erc20_one["contract"]
        print(f"Main user {self.user.environment.erc20_one['user'].address} balance: "
              f"{contract.functions.balanceOf(self.user.environment.erc20_one['user'].address).call()}")
        self.web3_client.send_erc20(
            self.user.environment.erc20_one["user"],
            self.account, 1000,
            contract.address,
            abi=contract.abi)

    @task
    def task_send_erc20_spl(self):
        """Send ERC20 tokens"""
        print("Send erc20spl ", self.account.address)
        contract = self.user.environment.erc20_one["contract"]
        recipient = random.choice(self.user.environment.shared.accounts)
        self.web3_client.send_erc20(
            self.account,
            recipient, 1,
            contract.address,
            abi=contract.abi)


class ERC20User(User):
    tasks = {
        ERC20SPLTasksSet: 1,
    }
