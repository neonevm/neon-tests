# Overview

Tests for rpc method neon_getPendingTransaction (check availability and basic functionality)

| Test case                                                                                                     | Description                                                                                     | XFailed |
|---------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|---------|
| TestRPCNeonGetPendingTransactions::test_neon_get_pending_scheduled_transaction_done                           | Send scheduled tx and check status is Done                                                      |         |
| TestRPCNeonGetPendingTransactions::test_neon_get_pending_scheduled_transaction_no_tx_body                     | Check status "NoTransactionBody"                                                                |         |
| TestRPCNeonGetPendingTransactions::test_multiple_scheduled_trx_with_failed_trx_skipped_and_wait_for_parent_tx | Send 4 transactions, check statuses Done, Skipped, NoTransactionBody, WaitForParentTransactions |         |