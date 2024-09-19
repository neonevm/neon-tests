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
        self.prepare_account()
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "common/Counter.sol", "0.8.10", account=self.account
        )
        self.contract = contract

    @task
    def task_run_iterative_tx(self):
        """Transferring funds to a random account"""
        tx = self.web3_client.make_raw_tx(self.account)
        instruction_tx = self.contract.functions.moreInstruction(
            0, 12000

        ).build_transaction(tx)
        trx = self.web3_client.send_transaction(self.account, instruction_tx)
        LOG.info("Transaction sent: %s", trx)


class NeonUser(User):
    tasks = {NeonIterativeTasksSet: 1}
