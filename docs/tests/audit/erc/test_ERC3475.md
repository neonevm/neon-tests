# Overview

Test for ERC-3475: Abstract Storage Bonds

# Tests list

| Test case                                                       | Description                             | XFailed |
|-----------------------------------------------------------------|-----------------------------------------|---------|
| TestAbstractStorageBonds::test_issue_bonds_to_lender            | Issue bonds to lender                   |         |
| TestAbstractStorageBonds::test_transfer_bonds                   | Transfer bonds                          |         |
| TestAbstractStorageBonds::test_transfer_approved_bonds          | Transfer approved bonds                 |         |
| TestAbstractStorageBonds::test_redeem_bonds                     | Redeem bonds                            |         |
| TestAbstractStorageBonds::test_redeem_more_than_balance         | Redeem more bonds than exist            |         |
| TestAbstractStorageBonds::test_burn                             | Check burn bonds                        |         |
| TestAbstractStorageBonds::test_batch_approve_transfer_allowance | Check several operations in transaction |         |
| TestAbstractStorageBonds::test_redeemed_supply                  | Check supply after redeem               |         |
| TestAbstractStorageBonds::test_burned_supply                    | Check supply after burn                 |         |
| TestAbstractStorageBonds::test_class_values                     | Get class parameters                    |         |
| TestAbstractStorageBonds::test_nonce_values                     | Get nonce values                        |         |
