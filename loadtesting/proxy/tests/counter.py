import logging


LOG = logging.getLogger(__name__)

# FIXME: Add new case to work with counter contract
# @tag("counter")
# @tag("contract")
# class CounterTasksSet(BaseResizingTasksSet):
#     """Implements Counter contracts base pipeline tasks"""
#
#     def on_start(self) -> None:
#         super(CounterTasksSet, self).on_start()
#         self._buffer = self.user.environment.shared.counter_contracts
#         self.contract_name = "Counter"
#         self.version = COUNTER_VERSION
#
#     @task(4)
#     @execute_before("task_block_number", "task_keeps_balance")
#     def task_increase_counter(self) -> None:
#         """Accounts increase"""
#         super(CounterTasksSet, self).task_resize("inc")
#
#     @task(2)
#     @execute_before("task_block_number", "task_keeps_balance")
#     def task_decrease_counter(self) -> None:
#         """Accounts decrease"""
#         super(CounterTasksSet, self).task_resize("dec")