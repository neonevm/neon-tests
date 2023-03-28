import logging

from locust import tag, task, User

from loadtesting.proxy.common.base import NeonProxyTasksSet

LOG = logging.getLogger(__name__)


@tag("send_neon")
class NeonIterativeTasksSet(NeonProxyTasksSet):
    """Deploy big nested contracts (actual for tracer)"""

    @task
    def task_deploy_big_tx(self):
        """Transferring funds to a random account"""
        LOG.info(f"Deploy contract: BigDeploy.sol from user {self.account.address}")
        contract, receipt = self.web3_client.deploy_and_get_contract(
            "BigDeploy.sol", "0.8.16", self.account, "Contract1"
        )
        LOG.info(f"Contract deployed: {receipt.contractAddress}")
        return receipt


class NeonUser(User):
    tasks = {NeonIterativeTasksSet: 1}
