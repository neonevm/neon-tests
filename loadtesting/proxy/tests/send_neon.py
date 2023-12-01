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
    recipient: str

    def on_start(self) -> None:
        super().on_start()
        super().setup()
        self.log = logging.getLogger(
            "neon-consumer[%s]" % self.account.address[-8:])
        self.nonce = self.web3_client.get_nonce(self.account)
        self.recipient = self.get_account()
    
    def get_balances(self):
        sender_balance = self.web3_client.get_balance(
            self.account.address)
        recipient_balance = self.web3_client.get_balance(
            self.recipient.address)
        return sender_balance, recipient_balance

    def get_account(self):
        return random.choice(self.user.environment.shared.accounts)

    def create_account(self):
        return self.web3_client.create_account()

    @task
    @execute_before("task_block_number")
    def task_send_neon(self):
        """Transferring funds to a random account"""
        # add credits to account
        self.nonce = self.web3_client.get_nonce(self.account)
        self.recipient = self.get_account()
        self.log.info(
            f"Send `neon` from {str(self.account.address)[-8:]} to {str(self.recipient.address)[-8:]}. nonce {self.nonce}"
        )

        tx = self.web3_client.send_neon(
            self.account, self.recipient, amount=1, nonce=self.nonce
        )

        return tx, self.web3_client.get_nonce(self.account)


class NeonUser(User):
    tasks = {NeonTasksSet: 1}
