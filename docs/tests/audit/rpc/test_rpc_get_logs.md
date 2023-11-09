# Overview

Tests for neon/eth rpc get logs

| Test case                                             | Description                                                                     | XFailed |
|-------------------------------------------------------|---------------------------------------------------------------------------------|---------|
| TestRpcGetLogs::test_get_logs_blockhash               | Get transaction logs by blockhash (eth & neon methods)                          |         |
| TestRpcGetLogs::test_get_logs_blockhash_empty_params  | Get transaction logs by blockhash with empty params (eth & neon methods)        |         |
| TestRpcGetLogs::test_get_logs_blockhash_negative_tags | Get transaction logs by blockhash with invalid params (eth & neon methods)      |         |
| TestRpcGetLogs::test_get_logs_negative_params         | Get transaction logs by blockhash with invalid params (eth & neon methods)      |         |
| TestRpcGetLogs::test_get_logs                         | Get transaction logs with different params (eth&neon methods)                   |         |
| TestRpcGetLogs::test_get_logs_eq_val                  | Get transaction logs with different params and check equal (eth & neon methods) |         |
| TestRpcGetLogs::test_get_logs_list_of_addresses       | Get transaction logs for list of addresses (eth & neon methods)                 |         |
| TestRpcGetLogs::test_filter_log_by_topics             | Get and filter logs by neon_getLogs, eth_getLogs                                |         |
