# Overview

Tests for transfer erc20_spl functionality

# Tests list

| Test case                                                                     | Description                                                                             | XFailed             |
|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|---------------------|
| TestErc20SplTransfer::test_send_spl_wrapped_token_from_one_account_to_another | Send 0, 1, 10, 100 tokens from one account to another                                   |                     |
| TestErc20SplTransfer::test_send_more_than_exist_on_account_spl                | Send erc20spl more than exist in account 1_000_000_000_000_000_000_000 and get an error |                     |
| TestErc20SplTransfer::test_send_negative_sum_from_account_spl                 | Send negative sum for spl and got an error                                              |                     |
| TestErc20SplTransfer::test_send_token_to_self_erc20                           | Send erc20 from account to this account                                                 |                     |
| TestErc20SplTransfer::test_check_erc_1820_transaction                         | Verify transaction without chain-id work                                                |                     |
| TestErc20SplTransfer::test_send_tokens_to_non_exist_acc                       | Send erc20 spl tockens tonon-existent in EVM account                                    |                     |
