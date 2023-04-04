import logging

from locust import tag, task, User

from loadtesting.proxy.common.base import NeonProxyTasksSet

LOG = logging.getLogger(__name__)


@tag("send_neon")
class NeonIterativeTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    contract = None

    def on_start(self) -> None:
        super().on_start()
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "Counter", "0.8.10", account=self.account
        )
        self.contract = contract

    @task
    def task_run_iterative_tx(self):
        """Transferring funds to a random account"""
        self.log.info(f"Run iterative tx from {str(self.account.address)[-8:]}.")
        instruction_tx = self.contract.functions.moreInstruction(
            0, 1500
        ).build_transaction(
            {
                "from": self.account.address,
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.account.address
                ),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        self.web3_client.send_transaction(self.account, instruction_tx)


class NeonUser(User):
    tasks = {NeonIterativeTasksSet: 1}
