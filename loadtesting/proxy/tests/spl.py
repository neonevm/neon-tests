@tag("spl")
class ERC20SPLTasksSet(ERC20BaseTasksSet):
    """Implements ERC20Wrapped base pipeline tasks"""

    _sol_client: tp.Optional["solana.rpc.api.Client"] = None

    def on_start(self) -> None:
        super(ERC20SPLTasksSet, self).on_start()
        self.version = ERC20_WRAPPER_VERSION
        self.contract_name = "erc20wrapper"
        self._buffer = self.user.environment.shared.erc20_wrapper_contracts
        self._sol_client = Client(self.credentials["solana_url"])

    @task(2)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy ERC20Wrapper contract"""
        super(ERC20SPLTasksSet, self).task_deploy_contract()

    @task(6)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_send_erc20_wrapped(self) -> None:
        """Send ERC20 tokens"""
        return super(ERC20SPLTasksSet, self).task_send_tokens()