# Overview

Tests for transfer functionality

# Tests list

| Test case                                                                   | Description                                                                               | XFailed             |
|-----------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|---------------------|
| TestTransfer::test_send_neon_from_one_account_to_another                    | Send 0, 0.1, 1, 1.1 neon from one account to another??                                    |                     |
| TestTransfer::test_send_erc20_token_from_one_account_to_another             | Deploy erc20 contract and send 0, 1, 10, 100 tokens from one account to another??         |                     |
| TestTransfer::test_send_spl_wrapped_token_from_one_account_to_another       | Deploy erc20spl contract and send 0, 1, 10, 100 tokens from one account to another??      |                     |
| TestTransfer::test_send_more_than_exist_on_account_neon                     | Send more than exist in account \[11_000_501, 10_000_000.1\] and get an error??           |                     |
| TestTransfer::test_send_more_than_exist_on_account_spl                      | Send erc20spl more than exist in account 1_000_000_000_000_000_000_000 and get an error?? |                     |
| TestTransfer::test_send_more_than_exist_on_account_erc20                    | Send erc20 more than exist in account 100_000 and get an error??                          |                     |
| TestTransfer::test_there_are_not_enough_neons_for_gas_fee                   | Send all neons from account and got error INSUFFICIENT_FUNDS                              |                     |
| TestTransfer::test_there_are_not_enough_neons_for_transfer                  | Send more neons than exist in account and got error INSUFFICIENT_FUNDS                    |                     |
| TestTransfer::test_send_negative_sum_from_account_neon                      | Send negative sum and got an error                                                        |                     |
| TestTransfer::test_send_negative_sum_from_account_spl                       | Send negative sum for spl and got an error                                                |                     |
| TestTransfer::test_send_negative_sum_from_account_erc20                     | Send negative sum for erc20spl and got an error                                           |                     |
| TestTransfer::test_send_token_to_self_neon                                  | Send neon from account to this account                                                    |                     |
| TestTransfer::test_send_token_to_self_erc20                                 | Send erc20 from account to this account                                                   |                     |
| TestTransfer::test_send_token_to_an_invalid_address                         | Send neon to invalid account address???                                                   |                     |
| TestTransfer::test_check_erc_1820_transaction                               | Verify transaction without chain-id work                                                  |                     |
| TestTransfer::test_transaction_does_not_fail_nested_contract                | Send neon to contract                                                                     |                     |
| TestTransactionsValidation::test_generate_bad_sign                          | Send transaction with invalid sign and got an error                                       |                     |
| TestTransactionsValidation::test_send_the_same_transactions_if_accepted     | Send one transaction twice                                                                |                     |
| TestTransactionsValidation::test_send_the_same_transactions_if_not_accepted | Send one transaction twice but first not accepted                                         |                     |
| TestTransactionsValidation::test_send_transaction_with_small_gas_amount     | Send transaction with not enough gas count                                                |                     |
| TestTransactionsValidation::test_send_transaction_with_old_nonce            | Send transaction with old nonce                                                           |                     |
| TestTransactionsValidation::test_send_too_big_transaction                   | Send a big transaction 256*1024 in data                                                   |                     |
| TestTransactionsValidation::test_send_transaction_with_small_gas_price      | Send a transaction with small gas price                                                   | Should be rewritten |
| TestTransactionsValidation::test_big_memory_value                           | Check memory overflow                                                                     | NDEV-628            |
| TestTransactionsValidation::test_transfer_gweis                             | Transfer values in gweis???                                                               | NDEV-628            |
