# Overview

Test for ERC-20: Tests for contracts created by createErc20ForSplMintable and createErc20ForSpl calls and fungible
tokens

# Tests list

| Test case                                                                     | Description                                                                 | XFailed |
|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------|---------|
| TestERC20wrapperContract::test_metaplex_data_mintable                         | Get metaplex data from mintable contract                                    |         |
| TestERC20wrapperContract::test_metaplex_data                                  | Get metaplex data from contract                                             |         |
| TestERC20wrapperContract::test_balanceOf                                      | Get user balance                                                            |         |
| TestERC20wrapperContract::test_balanceOf_with_incorrect_address               | Get balance from incorrect address                                          |         |
| TestERC20wrapperContract::test_mint_to_self                                   | Verify mint to sender                                                       |         |
| TestERC20wrapperContract::test_mint_to_another_account                        | Verify mint to another account                                              |         |
| TestERC20wrapperContract::test_mint_by_no_minter_role                         | Verify error if minter is not owner                                         |         |
| TestERC20wrapperContract::test_mint_with_incorrect_address                    | Mint  to incorrect address                                                  |         |
| TestERC20wrapperContract::test_mint_with_too_big_amount                       | Expect error on mint with big amount                                        |         |
| TestERC20wrapperContract::test_mint_no_enough_gas                             | Error on mint with not enough gas                                           |         |
| TestERC20wrapperContract::test_totalSupply                                    | Get totalSupply                                                             |         |
| TestERC20wrapperContract::test_totalSupply_mintable                           | Get totalSupply on mintable                                                 |         |
| TestERC20wrapperContract::test_decimals                                       | Get decimals                                                                |         |
| TestERC20wrapperContract::test_symbol                                         | Get symbol                                                                  |         |
| TestERC20wrapperContract::test_name                                           | Get name                                                                    |         |
| TestERC20wrapperContract::test_burn                                           | Verify burn work                                                            |         |
| TestERC20wrapperContract::test_burn_incorrect_address                         | Burn to incorrect address                                                   |         |
| TestERC20wrapperContract::test_burn_more_than_total_supply                    | Try to burn more than supply                                                |         |
| TestERC20wrapperContract::test_burn_no_enough_gas                             | Burn with not enough gas                                                    |         |
| TestERC20wrapperContract::test_burnFrom                                       | Verify burnFrom                                                             |         |
| TestERC20wrapperContract::test_burnFrom_without_allowance                     | Verify burnFrom without allowance                                           |         |
| TestERC20wrapperContract::test_burnFrom_more_than_allowanced                  | Verify burnFrom more allowed                                                |         |
| TestERC20wrapperContract::test_burnFrom_incorrect_address                     | Verify burnFrom with incorrect address                                      |         |
| TestERC20wrapperContract::test_burnFrom_no_enough_gas                         | Verify burnFrom with not enough gas                                         |         |
| TestERC20wrapperContract::test_approve_more_than_total_supply                 | Try to approve more than supply                                             |         |
| TestERC20wrapperContract::test_approve_incorrect_address                      | Try to approve incorrect address                                            |         |
| TestERC20wrapperContract::test_approve_no_enough_gas                          | Try to approve with not enough gas                                          |         |
| TestERC20wrapperContract::test_allowance_incorrect_address                    | Check allowance method with incorrect address                               |         |
| TestERC20wrapperContract::test_allowance_for_new_account                      | Check allowance method for new account                                      |         |
| TestERC20wrapperContract::test_transfer                                       | Verify transfer                                                             |         |
| TestERC20wrapperContract::test_transfer_incorrect_address                     | Verify transfer for incorrect address                                       |         |
| TestERC20wrapperContract::test_transfer_more_than_balance                     | Expect error on transfer more than balance                                  |         |
| TestERC20wrapperContract::test_transfer_no_enough_gas                         | Expect error with not enough gas                                            |         |
| TestERC20wrapperContract::test_transferFrom                                   | Verify transferFrom                                                         |         |
| TestERC20wrapperContract::test_transferFrom_without_allowance                 | Verify transferFrom without allowance                                       |         |
| TestERC20wrapperContract::test_transferFrom_more_than_allowance               | Verify transferFrom with more than allowance                                |         |
| TestERC20wrapperContract::test_transferFrom_incorrect_address                 | Verify transferFrom with incorrect address                                  |         |
| TestERC20wrapperContract::test_transferFrom_more_than_balance                 | Expect error on transferFrom more than balance                              |         |
| TestERC20wrapperContract::test_transferFrom_no_enough_gas                     | Expect error with not enough gas                                            |         |
| TestERC20wrapperContract::test_transferSolana                                 | Check transferSolana method                                                 |         |
| TestERC20wrapperContract::test_approveSolana                                  | Check approveSolana method                                                  |         |
| TestERC20wrapperContract::test_claim                                          | Check claim                                                                 |         |
| TestERC20wrapperContract::test_claimTo                                        | Check claimTo                                                               |         |
| TestMultipleActionsForERC20::test_mint_transfer_burn                          | Verify mint -> transfer -> burn in one transaction                          |         |
| TestMultipleActionsForERC20::test_mint_transfer_transfer_one_recipient        | Verify mint -> transfer -> transfer for one account in one transaction      |         |
| TestMultipleActionsForERC20::test_mint_transfer_transfer_different_recipients | Verify mint -> transfer -> transfer for several accounts in one transaction |         |
| TestMultipleActionsForERC20::test_transfer_mint_burn                          | Verify transfer -> mint -> burn in one transaction                          |         |
| TestMultipleActionsForERC20::test_transfer_mint_transfer_burn                 | Verify transfer -> mint -> transfer -> burn in one transaction              |         |
| TestMultipleActionsForERC20::test_mint_burn_transfer                          | Verify mint -> burn -> transfer in one transaction                          |         |
| TestMultipleActionsForERC20::test_mint_mint                                   | Verify mint -> mint in one transaction                                      |         |
| TestMultipleActionsForERC20::test_mint_mint_transfer_transfer                 | Verify mint -> mint -> transfer -> transfer in one transaction              |         |
| TestMultipleActionsForERC20::test_burn_transfer_burn_transfer                 | Verify burn -> transfer -> burn in one transaction                          |         |
| TestMultipleActionsForERC20::test_burn_mint_transfer                          | Verify burn -> mint -> transfer in one transaction                          |         |



