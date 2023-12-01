# Overview

Verify integration with SPL solana program

# Tests list

| Test case                                                      | Description                                            | XFailed |
|----------------------------------------------------------------|--------------------------------------------------------|---------|
| TestPrecompiledSplToken::test_get_mint_for_non_initialized_acc | Check getMint function for non initialized account     |         |
| TestPrecompiledSplToken::test_get_mint                         | Check getMint function for initialized account         |         |
| TestPrecompiledSplToken::test_get_account                      | Check getAccount method                                |         |
| TestPrecompiledSplToken::test_get_account_non_initialized_acc  | Check getAccount method for non initialized account    |         |
| TestPrecompiledSplToken::test_get_account_invalid_account      | Check getAccount method for invalid account            |         |
| TestPrecompiledSplToken::test_initialize_mint                  | Check initializeMint method                            |         |
| TestPrecompiledSplToken::test_initialize_acc_incorrect_mint    | Check initializeMint method with incorrect address     |         |
| TestPrecompiledSplToken::test_is_system_account                | Check isSystemAccount method                           |         |
| TestPrecompiledSplToken::test_find_account                     | Check findAccount method                               |         |
| TestPrecompiledSplToken::test_close_account                    | Check closeAccount method                              |         |
| TestPrecompiledSplToken::test_close_non_initialized_acc        | Check closeAccount method with non initialized account |         |
| TestPrecompiledSplToken::test_freeze_and_thaw                  | Check freeze method                                    |         |
| TestPrecompiledSplToken::test_freeze_non_initialized_account   | Check freeze method for non initialized account        |         |
| TestPrecompiledSplToken::test_freeze_non_initialized_token     | Check freeze method for non initialized token          |         |
| TestPrecompiledSplToken::test_freeze_with_not_associated_mint  | Check freeze method for not associated token           |         |
| TestPrecompiledSplToken::test_thaw_non_initialized_account     | Check thaw method for not initialized token            |         |
| TestPrecompiledSplToken::test_thaw_non_freezed_account         | Check thaw method for not freezed account              |         |
| TestPrecompiledSplToken::test_mint_to                          | Check mintTo method                                    |         |
| TestPrecompiledSplToken::test_mint_to_non_initialized_acc      | Check mintTo method to non initialized account         |         |
| TestPrecompiledSplToken::test_mint_to_non_initialized_token    | Check mintTo method to non initialized token           |         |
| TestPrecompiledSplToken::test_transfer                         | Check token transfer                                   |         |
| TestPrecompiledSplToken::test_transfer_to_non_initialized_acc  | Check token transfer to non initialized account        |         |
| TestPrecompiledSplToken::test_transfer_with_incorrect_signer   | Check token transfer with bad signer                   |         |
| TestPrecompiledSplToken::test_transfer_more_than_balance       | Check token transfer with big amount                   |         |
| TestPrecompiledSplToken::test_burn                             | Check burn method                                      |         |
| TestPrecompiledSplToken::test_burn_non_initialized_acc         | Check burn method for non initialized account          |         |
| TestPrecompiledSplToken::test_burn_more_then_balance           | Check burn method for big amount                       |         |
| TestPrecompiledSplToken::test_approve_and_revoke               | Check approve and revoke methods                       |         |
