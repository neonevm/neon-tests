# Overview

Verify that wrapped neon contract work

# Tests list

| Test case                                                 | Description                    | XFailed |
|-----------------------------------------------------------|--------------------------------|---------|
| TestWNeon::test_deposit_and_total_supply                  | Deposit and supply work        |         |
| TestWNeon::test_withdraw                                  | Check wNEON -> NEON            |         |
| TestWNeon::test_transfer_and_check_token_does_not_use_spl | Contract doesn't use SPL token |         |
| TestWNeon::test_transfer_from                             | Check transfer method          |         |
| TestWNeon::test_withdraw_wneon_from_neon_to_solana        | Withdraw wNEON to Solana       |         |

