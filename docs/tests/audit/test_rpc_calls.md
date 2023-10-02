# Overview

Tests for rpc endpoints (check availability and basic functionality)

# Tests list

| Test case                                                               | Description                                                | XFailed   |
|-------------------------------------------------------------------------|------------------------------------------------------------|-----------|
| TestRpcCalls::test_eth_call_without_params                              | Just call eth_call without params                          |           |
| TestRpcCalls::test_eth_call                                             | Call eth_call with with right but random data              |           |
| TestRpcCalls::test_eth_get_transaction_receipt_with_incorrect_hash      | Get receipt from random hash                               |           |
| TestRpcCalls::test_eth_gas_price                                        | Get gas price                                              |           |
| TestRpcCalls::test_eth_get_logs_blockhash                               | Get transaction logs by blockhash                          |           |
| TestRpcCalls::test_eth_get_logs_blockhash_negative_tags                 | Get transaction logs by blockhash with invalid params      | NDEV-2237 |
| TestRpcCalls::test_eth_get_logs_negative_params                         | Get transaction logs by blockhash with invalid params      |           |
| TestRpcCalls::test_eth_get_logs                                         | Get transaction logs with different params                 |           |
| TestRpcCalls::test_eth_get_logs_eq_val                                  | Get transaction logs with different params and check equal |           |
| TestRpcCalls::test_eth_get_balance                                      | Get sender balance with different state                    |           |
| TestRpcCalls::test_eth_get_code                                         | Get code                                                   |           |
| TestRpcCalls::test_web3_client_version                                  | Get web3_client_version                                    |           |
| TestRpcCalls::test_netversion                                           | Get net_version                                            |           |
| TestRpcCalls::test_eth_get_transaction_count                            | Get sender nonce                                           |           |
| TestRpcCalls::test_eth_send_raw_transaction                             | Basic check that sendRawTransaction work (send 1 neon)     |           |
| TestRpcCalls::test_eth_get_transaction_by_hash                          | Check method getTransactionByHash                          |           |
| TestRpcCalls::test_eth_get_transaction_receipt                          | Check response structure for getTransactionReceipt         |           |
| TestRpcCalls::test_eth_get_transaction_receipt_when_hash_doesnt_exist   | Check getTransactionReceipt if tx hash not exist           |           |
| TestRpcCalls::test_eth_get_block_by_hash                                | Get block and check structure                              |           |
| TestRpcCalls::test_eth_get_block_by_hash_with_incorrect_hash            | Try to get block with bad params                           |           |
| TestRpcCalls::test_eth_get_block_by_hash_with_not_existing_hash         | Try to get block with not exist hash                       |           |
| TestRpcCalls::test_eth_get_block_by_number_via_numbers                  | Try to get block by number                                 |           |
| TestRpcCalls::test_eth_get_block_by_number_with_incorrect_data          | Try to get block by number with bad params                 |           |
| TestRpcCalls::test_eth_get_block_by_number_with_not_exist_data          | Try to get block by number with bad params                 |           |
| TestRpcCalls::test_eth_block_number                                     | Get block by number                                        |           |
| TestRpcCalls::test_eth_get_storage_at                                   | Get storage                                                |           |
| TestRpcCalls::test_eth_mining                                           | Get eth_mining value                                       |           |
| TestRpcCalls::test_eth_syncing                                          | Get eth_syncing value                                      |           |
| TestRpcCalls::test_net_peer_count                                       | Get net peer count value                                   |           |
| TestRpcCalls::test_web3_sha3                                            | Get web3 sha3 value                                        |           |
| TestRpcCalls::test_eth_get_block_transaction_count_by_hash              | Get block transaction count in block by hash               |           |
| TestRpcCalls::test_eth_get_block_transaction_count_by_number            | Get block transaction count in block by hash               |           |
| TestRpcCalls::test_eth_get_work                                         | Get get work value                                         |           |
| TestRpcCalls::test_eth_hash_rate                                        | Get get hash rate value                                    |           |
| TestRpcCalls::test_check_unsupported_methods                            | Verify that unsupported methods return error               |           |
| TestRpcCalls::test_eth_get_block_by_number_via_tags                     | Get block by number with tags                              |           |
| TestRpcCalls::test_eth_get_transaction_by_block_number_and_index        | Get block by number with tags and index                    |           |
| TestRpcCalls::test_eth_get_transaction_by_block_hash_and_index          | Get block by hash with tags and index                      |           |
| TestRpcCalls::test_eth_get_transaction_by_block_number_and_index_by_tag | Get block by hash with tags and index                      |           |
| TestRpcCalls::test_get_evm_params                                       | Get neon evm parameters                                    |           |
| TestRpcCalls::test_neon_cli_version                                     | Get neon cli version                                       |           |
| TestRpcCalls::test_neon_get_logs                                        | Get logs by neon_getLogs parameter                         |           |
| TestRpcCalls::test_filter_log_by_topics                                 | Get and filter logs by neon_getLogs, eth_getLogs           |           |
| TestRpcCallsMoreComplex::test_eth_estimate_gas_with_big_int             | Estimate gas for a big contract                            |           |

