@tag("send_neon")
class NeonTasksSet(NeonProxyTasksSet):
    """Implements Neons transfer base pipeline tasks"""

    @task(1)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_send_neon(self) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Transferring funds to a random account"""
        # add credits to account
        recipient = random.choice(self.user.environment.shared.accounts)
        self.log.info(f"Send `neon` from {str(self.account.address)[-8:]} to {str(recipient.address)[-8:]}.")
        return self.web3_client.send_neon(self.account, recipient, amount=1)