# Overview

Tests for rpc endpoints (check availability and basic functionality)

# Tests list

| Test case                                                       | Description                                               | XFailed |
|-----------------------------------------------------------------|-----------------------------------------------------------|---------|
| TestRpcBaseCalls::test_eth_call_without_params                  | Just call eth_call without params                         |         |
| TestRpcBaseCalls::test_eth_call                                 | Call eth_call with with right but random data             |         |
| TestRpcBaseCalls::test_eth_gas_price                            | Get eth gas price                                         |         |
| TestRpcBaseCalls::test_eth_get_balance                          | Get sender balance with different state                   |         |
| TestRpcBaseCalls::test_eth_get_code                             | Get code                                                  |         |
| TestRpcBaseCalls::test_eth_get_code_sender_address              | Get code with sender address                              |         |
| TestRpcBaseCalls::test_eth_get_code_wrong_address               | Get code with the wrong address                           |         |
| TestRpcBaseCalls::test_web3_client_version                      | Get web3_client_version                                   |         |
| TestRpcBaseCalls::test_net_version                              | Get net_version                                           |         |
| TestRpcBaseCalls::test_eth_send_raw_transaction                 | Basic check that sendRawTransaction work (send 1 neon)    |         |
| TestRpcBaseCalls::test_eth_sendRawTransaction_max_size          | Get sendRawTransaction with max size of transaction       |         |
| TestRpcBaseCalls::test_eth_sendRawTransaction_max_contract_size | Get sendRawTransaction with max size of contract          |         |
| TestRpcBaseCalls::test_eth_block_number                         | Get block by number                                       |         |
| TestRpcBaseCalls::test_eth_block_number_next_block_different    | Get block by number 2 times, check that they're different |         |
| TestRpcBaseCalls::test_eth_get_storage_at                       | Get storage with different tags                           |         |
| TestRpcBaseCalls::test_eth_get_storage_at_eq_val                | Check equal values for get storage                        |         |
| TestRpcBaseCalls::test_eth_mining                               | Get eth_mining value                                      |         |
| TestRpcBaseCalls::test_eth_syncing                              | Get eth_syncing value                                     |         |
| TestRpcBaseCalls::test_net_peer_count                           | Get net peer count value                                  |         |
| TestRpcBaseCalls::test_web3_sha3                                | Get web3 sha3 value                                       |         |
| TestRpcBaseCalls::test_eth_get_work                             | Get get work value                                        |         |
| TestRpcBaseCalls::test_eth_hash_rate                            | Get get hash rate value                                   |         |
| TestRpcBaseCalls::test_check_unsupported_methods                | Verify that unsupported methods return error              |         |
| TestRpcBaseCalls::test_get_evm_params                           | Get neon evm parameters                                   |         |
