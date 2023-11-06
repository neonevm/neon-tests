import logging
import random
import string

from locust import User, events, tag, task
from solana.keypair import Keypair

from loadtesting.proxy.common.base import NeonProxyTasksSet
from utils.erc20wrapper import ERC20Wrapper
from utils.faucet import Faucet
from utils.web3client import NeonChainWeb3Client

LOG = logging.getLogger(__name__)


@events.test_start.add_listener
def prepare_one_contract_for_erc20(environment: "locust.env.Environment", **kwargs):
    neon_client = NeonChainWeb3Client(environment.credentials["proxy_url"])
    faucet = Faucet(environment.credentials["faucet_url"], neon_client)

    eth_account = neon_client.create_account()
    faucet.request_neon(eth_account.address, 10000)

    LOG.info("Deploy ERC20 contract for erc20spl test")
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    name = f"Test {symbol}"

    erc20_wrapper = ERC20Wrapper(
        neon_client,
        faucet,
        name,
        symbol,
        None,
        solana_account=Keypair.generate(),
        account=eth_account,
        mintable=True,
    )
    erc20_wrapper.deploy_wrapper(True)
    erc20_wrapper.mint_tokens(eth_account, eth_account.address, 18446744073709551615)

    environment.erc20_one = {
        "user": eth_account,
        "contract": erc20_wrapper,
    }


@tag("erc20spl")
class ERC20SPLTasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])
        contract = self.user.environment.erc20_one["contract"]
        contract.web3_client = self.web3_client
        contract.transfer(self.user.environment.erc20_one["user"], self.account, 1000)

    def get_account(self):
        return random.choice(self.user.environment.shared.accounts)

    @task
    def task_send_erc20_spl(self):
        """Send ERC20 tokens"""
        contract = self.user.environment.erc20_one["contract"]
        recipient = self.get_account()
        LOG.info(
            f"Send erc20spl token from {self.account.address[:8]} to {recipient.address[:8]}"
        )
        receipt = contract.transfer(self.account, recipient, 1)

        receipt = dict(receipt)
        receipt["contract"] = {"address": contract.contract.address}

        return receipt, self.web3_client.get_nonce(self.account)


class ERC20User(User):
    tasks = {
        ERC20SPLTasksSet: 1,
    }
