import random
import logging
import time

import web3
import requests
from locust import tag, task, User, events

from utils.web3client import NeonWeb3Client
from utils.faucet import Faucet

from loadtesting.proxy.common.base import NeonProxyTasksSet

LOG = logging.getLogger(__name__)

MAX_UINT_256 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
WNEON_ADDRESS = "0xf1041596da0499c3438e3B1Eb7b95354C6Aed1f5"
MORA_ADDRESSS = "0x6dcdd1620ce77b595e6490701416f6dbf20d2f67"
ROUTER_ADDRESS = "0xafa9ba8282db9ee8c89a63c99b093a9843436767"


@events.test_start.add_listener
def prepare_moraswap_contracts(environment: "locust.env.Environment", **kwargs):
    LOG.info("Prepare moraswap contracts")
    if environment.parsed_options.exclude_tags and "moraswap" in environment.parsed_options.exclude_tags:
        return
    if environment.parsed_options.tags and "moraswap" not in environment.parsed_options.tags:
        return

    neon_client = NeonWeb3Client(environment.credentials["proxy_url"], environment.credentials["network_id"])
    faucet = Faucet(environment.credentials["faucet_url"], neon_client)

    eth_account = neon_client.create_account()
    faucet.request_neon(eth_account.address, 10000)

    factory_abi = requests.get("https://raw.githubusercontent.com/moraswap/moraswap-core/master/abi/IMoraSwapFactory.json").json()
    router_abi = requests.get("https://raw.githubusercontent.com/moraswap/moraswap-core/master/abi/IMoraSwapRouter.json").json()
    # pair_abi = requests.get("https://github.com/moraswap/moraswap-core/blob/master/abi/IMoraSwapPair.json").json()
    token_abi = requests.get("https://raw.githubusercontent.com/moraswap/moraswap-core/master/abi/IMoraSwapERC20.json").json()

    factory_contract = neon_client.eth.contract(
        address="0x6dcDD1620Ce77B595E6490701416f6Dbf20D2f67",
        abi=factory_abi
    )
    router_contract = neon_client.eth.contract(
        address=web3.Web3.toChecksumAddress(ROUTER_ADDRESS),
        abi=router_abi
    )

    wneon_contract = neon_client.eth.contract(
        address=web3.Web3.toChecksumAddress(WNEON_ADDRESS),
        abi=token_abi
    )

    mora_contract = neon_client.eth.contract(
        address=web3.Web3.toChecksumAddress(MORA_ADDRESSS),
        abi=token_abi
    )

    # pair_address = factory_contract.functions.getPair(
    #     WNEON_ADDRESS,
    #     MORA_ADDRESSS
    # ).call()
    #
    # pair_contract = neon_client.eth.contract(
    #     address=pair_address,
    #     abi=pair_abi
    # )

    environment.moraswap = {
        "factory": factory_contract,
        "router": router_contract,
        # "pair": pair_contract,
        "wneon": wneon_contract,
        "mora": mora_contract
    }


@tag("moraswap")
class MoraswapTaskSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    def on_start(self) -> None:
        super(MoraswapTaskSet, self).on_start()
        wneon = self.user.environment.moraswap["wneon"]
        mora = self.user.environment.moraswap["mora"]

        for token in [wneon, mora]:
            self.log.info(f"Approve token by account {self.account.address}")
            trx = token.functions.approve(
                self.user.environment.moraswap["router"].address, MAX_UINT_256
            ).buildTransaction(
                {
                    "from": self.account.address,
                    "nonce": self.web3_client.get_nonce(self.account.address),
                    "gasPrice": self.web3_client.gas_price(),
                }
            )
            self.web3_client.send_transaction(self.account, trx)

    @task
    def task_swap_neon_mora(self):
        router = self.user.environment.moraswap["router"]
        token_a = self.user.environment.moraswap["wneon"]
        token_b = self.user.environment.moraswap["mora"]

        self.log.info("Swap token direct")
        swap_trx = router.functions.swapExactETHForTokens(
            web3.Web3.toWei(1, "ether"),
            [token_a.address, token_b.address],
            self.account.address,
            int(time.time()) + 1800,
        ).buildTransaction(
            {
                "from": self.account.address,
                "nonce": self.web3_client.get_nonce(self.account.address),
                "gasPrice": self.web3_client.gas_price(),
                "value": web3.Web3.toWei(1, "ether"),
            }
        )
        self.log.info("Swap transaction: %s" % self.web3_client.send_transaction(self.account, swap_trx, gas_multiplier=1.1))


class MoraswapUser(User):
    tasks = {
        MoraswapTaskSet: 1,
    }
