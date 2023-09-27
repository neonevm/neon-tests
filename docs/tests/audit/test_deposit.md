# Overview

Tests for check transfer tokens from solana->neon and neon->solana

# Tests list

| Test case                                                   | Description                                             | XFailed |
|-------------------------------------------------------------|---------------------------------------------------------|---------|
| TestDeposit::test_transfer_neon_from_solana_to_neon         | Verify transfer neon solana -> neon                     |         |
| TestDeposit::test_transfer_spl_token_from_solana_to_neon    | Verify transfer spl token solana -> neon                |         |
| TestWithdraw::test_success_withdraw_to_non_existing_account | Transfer Neon from Neon -> Solana to unexisting account |         |
| TestWithdraw::test_success_withdraw_to_existing_account     | Transfer Neon from Neon -> Solana to existing account   |         |
| TestWithdraw::test_failed_withdraw_non_divisible_amount     | Failed case to withdraw with bad amount                 |         |
| TestWithdraw::test_failed_withdraw_insufficient_balance     | Failed case to withdraw with bad amount                 |         |
