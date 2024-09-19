# Overview

Tests for check revert handling in different places

# Tests list

| Test case                                                                       | Description                                                          | XFailed |
|---------------------------------------------------------------------------------|----------------------------------------------------------------------|---------|
| TestContractReverting::test_constructor_raises_string_based_error               | Get revert inside contract constructor                               |         |
| TestContractReverting::test_constructor_raises_no_argument_error                | Get revert inside contract constructor if not enough arguments       |         |
| TestContractReverting::test_method_raises_string_based_error                    | Get revert inside contract method and return string error            |         |
| TestContractReverting::test_method_raises_trivial_error                         | Get revert inside contract method without error                      |         |
| TestContractReverting::test_nested_contract_revert                              | Get revert from the chain of contracts                               |         |
| TestContractReverting::test_eth_call_revert                                     | Get revert via eth_call                                              |         |
| TestContractReverting::test_gas_limit_reached                                   | Get gas limit reached revert                                         |         |
| TestContractReverting::test_custom_error_revert                                 | Get custom error revert                                              |         |
| TestContractReverting::test_assert_revert                                       | Get assert error revert                                              |         |
| TestContractReverting::test_method_raises_string_based_error_caller             | String error for other contract method using eth_call                |         |
| TestContractReverting::test_method_raises_string_based_error_tx_caller          | String error for other contract method using eth_estimateGas         |         |
| TestContractReverting::test_method_raises_string_based_error_tx_with_gas_caller | String error for other contract method using eth_sendRawTransaction  |         |
| TestContractReverting::test_method_raises_trivial_error_caller                  | require(false) for other contract method using eth_call              |         |
| TestContractReverting::test_method_raises_trivial_error_tx_caller               | require(false) for other contract method using eth_estimateGas       |         |
| TestContractReverting::test_method_raises_trivial_error_tx_with_gas_caller      | require(false) for other contract method using eth_sendRawTransaction|         |
| TestContractReverting::test_custom_error_revert_caller                          | Custom error for other contract method using eth_call                |         |
| TestContractReverting::test_custom_error_revert_tx_caller                       | Custom error for other contract method using eth_estimateGas         |         |
| TestContractReverting::test_custom_error_revert_tx_with_gas_caller              | Custom error for other contract method using eth_sendRawTransaction  |         |
| TestContractReverting::test_assert_revert_caller                                | Assert error for other contract method using eth_call                |         |
| TestContractReverting::test_assert_revert_tx_caller                             | Assert error for other contract method using eth_estimateGas         |         |
| TestContractReverting::test_assert_revert_tx_with_gas_caller                    | Assert error for other contract method using eth_sendRawTransaction  |         |
| TestContractReverting::test_deploy_failed_contract_caller                       | Deploy contract with error in constructor using eth_call             |         |
| TestContractReverting::test_deploy_failed_contract_tx_caller                    | Deploy contract with error in constructor using eth_estimateGas      |         |
| TestContractReverting::test_deploy_failed_contract_tx_with_gas_caller           | Deploy contract with error in constructor via eth_sendRawTransaction |         |
| TestContractReverting::test_contract_memory_overflow_call                       | Deploy contract with potential overflow expected success             |         |
