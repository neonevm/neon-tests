import random
import logging

from locust import tag, task, User

from loadtesting.proxy.common.base import NeonProxyTasksSet
from loadtesting.proxy.common.events import execute_before

LOG = logging.getLogger(__name__)


@tag("send_neon")
class NeonTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    nonce: int

    def on_start(self) -> None:
        super().on_start()
        self.nonce = self.web3_client.get_nonce(self.account)

    @task
    @execute_before("task_block_number")
    def task_send_neon(self):
        """Transferring funds to a random account"""
        # add credits to account
        self.nonce = self.web3_client.get_nonce(self.account)
        recipient = random.choice(self.user.environment.shared.accounts)
        self.log.info(
            f"Send `neon` from {str(self.account.address)[-8:]} to {str(recipient.address)[-8:]}. nonce {self.nonce}"
        )
        tx = self.web3_client.send_neon(
            self.account, recipient, amount=1, nonce=self.nonce
        )
        return tx


class NeonUser(User):
    tasks = {NeonTasksSet: 1}
