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
        sender_balance_before = self.web3_client.get_balance(
            self.account.address)
        recipient_balance_before = self.web3_client.get_balance(
            recipient.address)

        amount = random.randint(1, int(sender_balance_before / 2))
        tx = self.web3_client.send_neon(
            self.account, recipient, amount=amount, nonce=self.nonce
        )
        recipient_nonce = self.web3_client.get_nonce(recipient)

        sender_balance_after = self.web3_client.get_balance(
            self.account.address)
        recipient_balance_after = self.web3_client.get_balance(
            recipient.address)
        
        info = {
            "sender_balance_before": f"{sender_balance_before}",
            "sender_balance_after": f"{sender_balance_after}",
            "recipient_nonce": f"{recipient_nonce}",
            "recipient_balance_before": f"{recipient_balance_before}",
            "recipient_balance_after": f"{recipient_balance_after}",
            "amount": amount,
            "type": "neon",
        }
        return tx, info


class NeonUser(User):
    tasks = {NeonTasksSet: 1}
