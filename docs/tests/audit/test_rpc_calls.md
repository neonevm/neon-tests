# Overview

Tests for rpc endpoints (check availability and basic functionality)

# Tests list

| Test case                                                                                  | Description                                                                     | XFailed |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|---------|
| TestRpcBaseCalls::test_eth_call_without_params                                             | Just call eth_call without params                                               |         |
| TestRpcBaseCalls::test_eth_call                                                            | Call eth_call with with right but random data                                   |         |
| TestRpcBaseCalls::test_eth_gas_price                                                       | Get eth gas price                                                               |         |
| TestRpcBaseCalls::test_eth_get_balance                                                     | Get sender balance with different state                                         |         |
| TestRpcBaseCalls::test_eth_get_code                                                        | Get code                                                                        |         |
| TestRpcBaseCalls::test_eth_get_code_sender_address                                         | Get code with sender address                                                    |         |
| TestRpcBaseCalls::test_eth_get_code_wrong_address                                          | Get code with the wrong address                                                 |         |
| TestRpcBaseCalls::test_web3_client_version                                                 | Get web3_client_version                                                         |         |
| TestRpcBaseCalls::test_net_version                                                         | Get net_version                                                                 |         |
| TestRpcBaseCalls::test_eth_send_raw_transaction                                            | Basic check that sendRawTransaction work (send 1 neon)                          |         |
| TestRpcBaseCalls::test_eth_sendRawTransaction_max_size                                     | Get sendRawTransaction with max size of transaction                             |         |
| TestRpcBaseCalls::test_eth_sendRawTransaction_max_contract_size                            | Get sendRawTransaction with max size of contract                                |         |
| TestRpcBaseCalls::test_eth_block_number                                                    | Get block by number                                                             |         |
| TestRpcBaseCalls::test_eth_block_number_next_block_different                               | Get block by number 2 times, check that they're different                       |         |
| TestRpcBaseCalls::test_eth_get_storage_at                                                  | Get storage with different tags                                                 |         |
| TestRpcBaseCalls::test_eth_get_storage_at_eq_val                                           | Check equal values for get storage                                              |         |
| TestRpcBaseCalls::test_eth_mining                                                          | Get eth_mining value                                                            |         |
| TestRpcBaseCalls::test_eth_syncing                                                         | Get eth_syncing value                                                           |         |
| TestRpcBaseCalls::test_net_peer_count                                                      | Get net peer count value                                                        |         |
| TestRpcBaseCalls::test_web3_sha3                                                           | Get web3 sha3 value                                                             |         |
| TestRpcBaseCalls::test_eth_get_work                                                        | Get get work value                                                              |         |
| TestRpcBaseCalls::test_eth_hash_rate                                                       | Get get hash rate value                                                         |         |
| TestRpcBaseCalls::test_check_unsupported_methods                                           | Verify that unsupported methods return error                                    |         |
| TestRpcBaseCalls::test_get_evm_params                                                      | Get neon evm parameters                                                         |         |
|                                                                                            |                                                                                 |         |
| TestNeonRPCBaseCalls::test_neon_gas_price_negative                                         | Get neon gas price, negative cases                                              |         |
| TestNeonRPCBaseCalls::test_neon_gas_price                                                  | Get neon gas price                                                              |         |
| TestNeonRPCBaseCalls::test_neon_cli_version                                                | Get neon cli version                                                            |         |
| TestNeonRPCBaseCalls::test_neon_get_solana_transaction_by_neon_transaction                 | Positive cases                                                                  |         |
| TestNeonRPCBaseCalls::test_neon_get_solana_transaction_by_neon_transaction_list_of_tx      | List of sol tx                                                                  |         |
| TestNeonRPCBaseCalls::test_neon_get_solana_transaction_by_neon_transaction_negative        | Negative cases                                                                  |         |
| TestNeonRPCBaseCalls::test_neon_get_solana_transaction_by_neon_transaction_non_existent_tx | Non existent transaction, empty response                                        |         |
|                                                                                            |                                                                                 |         |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_hash_negative          | Get block transaction count in block by hash, negative cases                    |         |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_hash                   | Get block transaction count in block by hash                                    |         |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_number_negative        | Get block transaction count in block by number, negative cases                  |         |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_number_tags            | Get block transaction count in block by number, tags params                     |         |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_number                 | Get block transaction count in block by number                                  |         |
|                                                                                            |                                                                                 |         |
| TestRpcGetBlock::test_eth_get_block_by_hash                                                | Get block and check structure                                                   |         |
| TestRpcGetBlock::test_eth_get_block_by_hash_with_incorrect_hash                            | Try to get block with bad params                                                |         |
| TestRpcGetBlock::test_eth_get_block_by_hash_with_not_existing_hash                         | Try to get block with not exist hash                                            |         |
| TestRpcGetBlock::test_eth_get_block_by_number_via_numbers                                  | Try to get block by number                                                      |         |
| TestRpcGetBlock::test_eth_get_block_by_number_with_incorrect_data                          | Try to get block by number with bad params                                      |         |
| TestRpcGetBlock::test_eth_get_block_by_number_with_not_exist_data                          | Try to get block by number with bad params                                      |         |
| TestRpcGetBlock::test_eth_get_block_by_number_via_tags                                     | Get block by number with tags                                                   |         |
|                                                                                            |                                                                                 |         |
| TestRpcGetLogs::test_get_logs_blockhash                                                    | Get transaction logs by blockhash (eth & neon methods)                          |         |
| TestRpcGetLogs::test_get_logs_blockhash_empty_params                                       | Get transaction logs by blockhash with empty params (eth & neon methods)        |         |
| TestRpcGetLogs::test_get_logs_blockhash_negative_tags                                      | Get transaction logs by blockhash with invalid params (eth & neon methods)      |         |
| TestRpcGetLogs::test_get_logs_negative_params                                              | Get transaction logs by blockhash with invalid params (eth & neon methods)      |         |
| TestRpcGetLogs::test_get_logs                                                              | Get transaction logs with different params (eth&neon methods)                   |         |
| TestRpcGetLogs::test_get_logs_eq_val                                                       | Get transaction logs with different params and check equal (eth & neon methods) |         |
| TestRpcGetLogs::test_get_logs_list_of_addresses                                            | Get transaction logs for list of addresses (eth & neon methods)                 |         |
| TestRpcGetLogs::test_filter_log_by_topics                                                  | Get and filter logs by neon_getLogs, eth_getLogs                                |         |
|                                                                                            |                                                                                 |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_block_number_and_index                  | Get block by number with tags and index                                         |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_block_hash_and_index                    | Get block by hash with tags and index                                           |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_block_number_and_index_by_tag           | Get block by hash with tags and index                                           |         |
| TestRpcGetTransaction::test_get_transaction_receipt_with_incorrect_hash                    | Get receipt from random hash (eth & neon methods)                               |         |
| TestRpcGetTransaction::test_eth_get_transaction_count                                      | Get transaction count                                                           |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_hash_negative                           | Get transaction by hash, negative cases                                         |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_hash                                    | Check method getTransactionByHash                                               |         |
| TestRpcGetTransaction::test_get_transaction_receipt                                        | Check response structure for getTransactionReceipt (eth & neon methods)         |         |
| TestRpcGetTransaction::test_get_transaction_receipt_when_hash_doesnt_exist                 | Check getTransactionReceipt if tx hash not exist (eth & neon methods)           |         |
| TestRpcGetTransaction::test_eth_get_transaction_receipt_when_hash_doesnt_exist             | Non existent hash as param                                                      |         |
| TestRpcGetTransaction::test_neon_get_transaction_by_sender_nonce_negative                  | Negative cases with posible error checkes                                       |         |
| TestRpcGetTransaction::test_neon_get_transaction_by_sender_nonce_plus_one                  | Request nonce+1, which is not exist                                             |         |
| TestRpcGetTransaction::test_neon_get_transaction_by_sender_nonce                           | Positive cases                                                                  |         |
|                                                                                            |                                                                                 |         |
| TestRpcEstimateGas::test_eth_estimate_gas                                                  | Get estimate gas for contract                                                   |         |
| TestRpcEstimateGas::test_eth_estimate_gas_negative                                         | Get estimate gas without params                                                 |         |
| TestRpcEstimateGas::test_eth_estimate_gas_with_big_int                                     | Get estimate gas for a big contract                                             |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_send_neon                                        | Get estimate gas for send neon transfer operation                               |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_erc20                                            | Get estimate gas for erc20 transfer operation                                   |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_spl                                              | Get estimate gas for spl transfer operation                                     |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_get_value                               | Get estimate gas for getting value from the contract                            |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_set_value                               | Get estimate gas for setting value in the contract                              |         |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_calls_another_contract                  | Get estimate gas for calling function in one contract from another              |         |

