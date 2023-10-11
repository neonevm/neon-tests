# Overview

Tests for transfer erc20 functionality

# Tests list

| Test case                                                            | Description                                                    | XFailed             |
|----------------------------------------------------------------------|----------------------------------------------------------------|---------------------|
| TestErc20Transfer::test_send_erc20_token_from_one_account_to_another | Send 0, 1, 10, 100 tokens from one account to another          |                     |
| TestErc20Transfer::test_send_more_than_exist_on_account_erc20        | Send erc20 more than exist in account 100_000 and get an error |                     |
| TestErc20Transfer::test_send_negative_sum_from_account_erc20         | Send negative sum for erc20 and got an error                   |                     |
| TestErc20Transfer::test_send_token_to_self_erc20                     | Send erc20 from account to this account                        |                     |
| TestErc20Transfer::test_send_tokens_to_non_exist_acc                 | Send erc20 tokens to non-existent in EVM account address       |                     |