# Overview

Tests for check revert handling in different places

# Tests list

| Test case                                                         | Description                                                    | XFailed |
|-------------------------------------------------------------------|----------------------------------------------------------------|---------|
| TestContractReverting::test_constructor_raises_string_based_error | Get revert inside contract constructor                         |         |
| TestContractReverting::test_constructor_raises_no_argument_error  | Get revert inside contract constructor if not enough arguments |         |
| TestContractReverting::test_method_raises_string_based_error      | Get revert inside contract method and return string error      |         |
| TestContractReverting::test_method_raises_trivial_error           | Get revert inside contract method without error                |         |
| TestContractReverting::test_nested_contract_revert                | Get revert from the chain of contracts                         |         |
| TestContractReverting::test_eth_call_revert                       | Get revert via eth_call                                        |         |
| TestContractReverting::test_gas_limit_reached                     | Get gas limit reached revert                                   |         |
| TestContractReverting::test_custom_error_revert                   | Get custom error revert                                        |         |
| TestContractReverting::test_assert_revert                         | Get assert error revert                                        |         |
