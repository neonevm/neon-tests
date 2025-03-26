import logging
import random
import string
import threading

from locust import User, events, tag, task, env
from solders.keypair import Keypair

from loadtesting.proxy.common.base import NeonProxyTasksSet
from utils.erc20wrapper import ERC20NewWrapper
from utils.faucet import Faucet
from utils.web3client import NeonChainWeb3Client

LOG = logging.getLogger(__name__)
USER_LOCK = threading.Lock()


@events.test_start.add_listener
def prepare_one_contract_for_erc20(environment: env.Environment, **kwargs):
    neon_client = NeonChainWeb3Client(environment.credentials["proxy_url"])
    faucet = Faucet(environment.credentials["faucet_url"], neon_client)

    eth_account = neon_client.create_account()
    faucet.request_neon(eth_account.address, 10000)

    LOG.info("Deploy ERC20 contract for erc20spl test")
    symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
    name = f"Test {symbol}"

    erc20_wrapper = ERC20NewWrapper(
        neon_client,
        faucet,
        name,
        symbol,
        None,
        solana_account=Keypair(),
        account=eth_account,
        mintable=True,
    )
    erc20_wrapper.deploy_wrapper(True)
    erc20_wrapper.mint_tokens(eth_account, eth_account.address, 18446744073709551615)

    environment.erc20_one = {"contract": erc20_wrapper, "accounts": []}

    for _ in range(environment.parsed_options.num_users):
        print(f"Creating {_} eth like account...")
        acc = neon_client.create_account()
        erc20_wrapper.transfer(eth_account, acc, 10_000)
        environment.erc20_one["accounts"].append(acc)


@tag("erc20spl")
class ERC20SPLTasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger("neon-consumer[%s]" % self.account.address[-8:])

        with USER_LOCK:
            if not self.user.environment.erc20_one["accounts"]:
                raise RuntimeError("Too little users")
            self.account = self.user.environment.erc20_one["accounts"].pop(0)
            self.check_balance(self.account)

    def on_stop(self):
        if self.account is not None:
            with USER_LOCK:
                self.user.environment.erc20_one["accounts"].append(self.account)
                LOG.info(f"Returned user: {self.account.address}")

    def get_account(self):
        return random.choice(self.user.environment.shared.accounts)

    @task
    def task_send_erc20_spl(self):
        """Send ERC20 tokens"""
        contract = self.user.environment.erc20_one["contract"]
        contract.web3_client = self.web3_client
        recipient = self.get_account()
        LOG.info(f"Send erc20spl token from {self.account.address[:8]} to {recipient.address[:8]}")
        receipt = contract.transfer(self.account, recipient, 1)
        LOG.info(dict(receipt))
        assert receipt["status"] == 1, receipt


class ERC20User(User):
    tasks = {
        ERC20SPLTasksSet: 1,
    }
