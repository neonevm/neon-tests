# Overview

Tests for neon transfer functionality

# Tests list

| Test case                                                                 | Description                                                                             | XFailed             |
|---------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|---------------------|
| TestNeonTransfer::test_send_neon_from_one_account_to_another              | Send 0, 0.1, 1, 1.1 neon from one account to another                                    |                     |
| TestNeonTransfer::test_send_more_than_exist_on_account_neon               | Send more than exist in account \[11_000_501, 10_000_000.1\] and get an error           |                     |
| TestNeonTransfer::test_there_are_not_enough_neons_for_gas_fee             | Send all neons from account and got error INSUFFICIENT_FUNDS                            |                     |
| TestNeonTransfer::test_send_token_to_self_neon                            | Send neon from account to this account                                                  |                     |
| TestNeonTransfer::test_send_token_to_an_invalid_address                   | Send neon to invalid account address                                                    |                     |
| TestNeonTransfer::test_erc_1820_transaction                               | Verify transaction without chain-id works                                               |                     |
| TestNeonTransfer::test_transaction_does_not_fail_nested_contract          | Send neon to contract                                                                   |                     |
