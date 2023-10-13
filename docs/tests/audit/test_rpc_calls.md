# Overview

Tests for rpc endpoints (check availability and basic functionality)

# Tests list

| Test case                                                                           | Description                                                        | XFailed   |
|-------------------------------------------------------------------------------------|--------------------------------------------------------------------|-----------|
| TestRpcCalls::test_eth_call_without_params                                          | Just call eth_call without params                                  |           |
| TestRpcCalls::test_eth_call                                                         | Call eth_call with with right but random data                      |           |
| TestRpcCalls::test_eth_gas_price                                                    | Get gas price                                                      |           |
| TestRpcCalls::test_eth_get_balance                                                  | Get sender balance with different state                            |           |
| TestRpcCalls::test_eth_get_code                                                     | Get code                                                           |           |
| TestRpcCalls::test_eth_get_code_sender_address                                      | Get code with sender address                                       |           |
| TestRpcCalls::test_eth_get_code_wrong_address                                       | Get code with the wrong address                                    |           |
| TestRpcCalls::test_web3_client_version                                              | Get web3_client_version                                            |           |
| TestRpcCalls::test_net_version                                                      | Get net_version                                                    |           |
| TestRpcCalls::test_eth_send_raw_transaction                                         | Basic check that sendRawTransaction work (send 1 neon)             |           |
| TestRpcCalls::test_eth_sendRawTransaction_max_size                                  | Get sendRawTransaction with max size of transaction                |           |
| TestRpcCalls::test_eth_sendRawTransaction_max_contract_size                         | Get sendRawTransaction with max size of contract                   |           |
| TestRpcCalls::test_eth_block_number                                                 | Get block by number                                                |           |
| TestRpcCalls::test_eth_block_number_next_block_different                            | Get block by number 2 times, check that they're different          |           |
| TestRpcCalls::test_eth_get_storage_at                                               | Get storage with different tags                                    |           |
| TestRpcCalls::test_eth_get_storage_at_eq_val                                        | Check equal values for get storage                                 |           |
| TestRpcCalls::test_eth_mining                                                       | Get eth_mining value                                               |           |
| TestRpcCalls::test_eth_syncing                                                      | Get eth_syncing value                                              |           |
| TestRpcCalls::test_net_peer_count                                                   | Get net peer count value                                           |           |
| TestRpcCalls::test_web3_sha3                                                        | Get web3 sha3 value                                                |           |
| TestRpcCalls::test_eth_get_work                                                     | Get get work value                                                 |           |
| TestRpcCalls::test_eth_hash_rate                                                    | Get get hash rate value                                            |           |
| TestRpcCalls::test_check_unsupported_methods                                        | Verify that unsupported methods return error                       |           |
| TestRpcCalls::test_get_evm_params                                                   | Get neon evm parameters                                            |           |
| TestRpcCalls::test_neon_cli_version                                                 | Get neon cli version                                               |           |
|                                                                                     |                                                                    |           |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_hash_negative   | Get block transaction count in block by hash, negative cases       |           |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_hash            | Get block transaction count in block by hash                       |           |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_number_negative | Get block transaction count in block by number, negative cases     |           |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_number_tags     | Get block transaction count in block by number, tags params        |           |
| TestRpcGetBlockTransaction::test_eth_get_block_transaction_count_by_number          | Get block transaction count in block by number                     |           |
|                                                                                     |                                                                    |           |
| TestRpcGetBlock::test_eth_get_block_by_hash                                         | Get block and check structure                                      |           |
| TestRpcGetBlock::test_eth_get_block_by_hash_with_incorrect_hash                     | Try to get block with bad params                                   |           |
| TestRpcGetBlock::test_eth_get_block_by_hash_with_not_existing_hash                  | Try to get block with not exist hash                               |           |
| TestRpcGetBlock::test_eth_get_block_by_number_via_numbers                           | Try to get block by number                                         |           |
| TestRpcGetBlock::test_eth_get_block_by_number_with_incorrect_data                   | Try to get block by number with bad params                         |           |
| TestRpcGetBlock::test_eth_get_block_by_number_with_not_exist_data                   | Try to get block by number with bad params                         |           |
| TestRpcGetBlock::test_eth_get_block_by_number_via_tags                              | Get block by number with tags                                      |           |
|                                                                                     |                                                                    |           |
| TestRpcGetLogs::test_eth_get_logs_blockhash                                         | Get transaction logs by blockhash                                  |           |
| TestRpcGetLogs::test_eth_get_logs_blockhash_empty_params                            | Get transaction logs by blockhash with empty params                |           |
| TestRpcGetLogs::test_eth_get_logs_blockhash_negative_tags                           | Get transaction logs by blockhash with invalid params              | NDEV-2237 |
| TestRpcGetLogs::test_eth_get_logs_negative_params                                   | Get transaction logs by blockhash with invalid params              |           |
| TestRpcGetLogs::test_eth_get_logs                                                   | Get transaction logs with different params                         |           |
| TestRpcGetLogs::test_eth_get_logs_eq_val                                            | Get transaction logs with different params and check equal         |           |
| TestRpcGetLogs::test_eth_get_logs_list_of_addresses                                 | Get transaction logs for list of addresses                         |           |
| TestRpcGetLogs::test_neon_get_logs                                                  | Get logs by neon_getLogs parameter                                 |           |
| TestRpcGetLogs::test_filter_log_by_topics                                           | Get and filter logs by neon_getLogs, eth_getLogs                   |           |
|                                                                                     |                                                                    |           |
| TestRpcGetTransaction::test_eth_get_transaction_by_block_number_and_index           | Get block by number with tags and index                            |           |
| TestRpcGetTransaction::test_eth_get_transaction_by_block_hash_and_index             | Get block by hash with tags and index                              |           |
| TestRpcGetTransaction::test_eth_get_transaction_by_block_number_and_index_by_tag    | Get block by hash with tags and index                              |           |
| TestRpcGetTransaction::test_eth_get_transaction_receipt_with_incorrect_hash         | Get receipt from random hash                                       |           |
| TestRpcGetTransaction::test_eth_get_transaction_count                               | Get transaction count                                              |           |
| TestRpcGetTransaction::test_eth_get_transaction_by_hash_negative                    | Get transaction by hash, negative cases                            |           |
| TestRpcGetTransaction::test_eth_get_transaction_by_hash                             | Check method getTransactionByHash                                  |           |
| TestRpcGetTransaction::test_eth_get_transaction_receipt                             | Check response structure for getTransactionReceipt                 |           |
| TestRpcGetTransaction::test_eth_get_transaction_receipt_when_hash_doesnt_exist      | Check getTransactionReceipt if tx hash not exist                   |           |
|                                                                                     |                                                                    |           |
| TestRpcEstimateGas::test_eth_estimate_gas                                           | Get estimate gas for contract                                      | NDEV-2310 |
| TestRpcEstimateGas::test_eth_estimate_gas_negative                                  | Get estimate gas without params                                    | NDEV-2310 |
| TestRpcEstimateGas::test_eth_estimate_gas_with_big_int                              | Get estimate gas for a big contract                                |           |
| TestRpcEstimateGas::test_rpc_estimate_gas_send_neon                                 | Get estimate gas for send neon transfer operation                  |           |
| TestRpcEstimateGas::test_rpc_estimate_gas_erc20                                     | Get estimate gas for erc20 transfer operation                      |           |
| TestRpcEstimateGas::test_rpc_estimate_gas_spl                                       | Get estimate gas for spl transfer operation                        |           |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_get_value                        | Get estimate gas for getting value from the contract               |           |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_set_value                        | Get estimate gas for setting value in the contract                 |           |
| TestRpcEstimateGas::test_rpc_estimate_gas_contract_calls_another_contract           | Get estimate gas for calling function in one contract from another |           |

