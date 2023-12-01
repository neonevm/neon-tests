# Overview

Verify EIP-1052: EXTCODEHASH opcode

# Tests list

| Test case                                                                     | Description                                     | XFailed |
|-------------------------------------------------------------------------------|-------------------------------------------------|---------|
| TestExtCodeHashOpcode::test_extcodehash_for_contract_address                  | Execute via eth_call                            |         |
| TestExtCodeHashOpcode::test_extcodehash_with_send_tx_for_contract_address     | Execute via transaction                         |         |
| TestExtCodeHashOpcode::test_extcodehash_for_empty_account                     | Execute for empty account and eth_call          |         |
| TestExtCodeHashOpcode::test_extcodehash_with_send_tx_for_empty_account        | Execute for empty account via transaction       |         |
| TestExtCodeHashOpcode::test_extcodehash_for_non_existing_account              | Execute for not existing account and eth_call   |         |
| TestExtCodeHashOpcode::test_extcodehash_with_send_tx_for_non_existing_account | Execute for not existing account in transaction |         |
| TestExtCodeHashOpcode::test_extcodehash_for_destroyed_contract                | Execute for destroyed contract with eth_call    |         |
| TestExtCodeHashOpcode::test_extcodehash_with_send_tx_for_destroyed_contract   | Execute for destroyed contract in transaction   |         |
| TestExtCodeHashOpcode::test_extcodehash_for_reverted_destroyed_contract       | Execute for revert contract in eth_call         |         |
| TestExtCodeHashOpcode::test_extcodehash_for_precompiled_contract              | Execute for precompiled contract in eth_call    |         |
| TestExtCodeHashOpcode::test_extcodehash_with_send_tx_for_precompiled_contract | Execute for precompiled contract in transaction |         |
