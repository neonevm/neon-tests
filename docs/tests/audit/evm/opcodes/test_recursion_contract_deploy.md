# Overview

Check how to evm handle recursion in contracts

# Tests list

| Test case                                                                  | Description                                         | XFailed |
|----------------------------------------------------------------------------|-----------------------------------------------------|---------|
| TestContractRecursion::test_deploy_with_recursion                          | Recursion in deploy                                 |         |
| TestContractRecursion::test_deploy_with_recursion_via_create2              | Recursion in deploy via create2                     |         |
| TestContractRecursion::test_deploy_with_recursion_via_create               | Recursion in deploy via create                      |         |
| TestContractRecursion::test_deploy_to_the_same_address_via_create2_one_trx | Recursion in deploy via create2 in the same address |         |
| TestContractRecursion::test_recursion_in_function_calls                    | Recursion in contract function                      |         |
| TestContractRecursion::test_recursion_in_constructor_calls                 | Recursion in contract constructor                   |         |
