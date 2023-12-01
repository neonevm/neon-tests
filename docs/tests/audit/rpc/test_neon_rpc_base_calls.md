# Overview

Tests for neon rpc base endpoints (check availability and basic functionality)

| Test case                                                                                  | Description                              | XFailed |
|--------------------------------------------------------------------------------------------|------------------------------------------|---------|
| TestNeonRPCBaseCalls::test_neon_gas_price_negative                                         | Get neon gas price, negative cases       |         |
| TestNeonRPCBaseCalls::test_neon_gas_price                                                  | Get neon gas price                       |         |
| TestNeonRPCBaseCalls::test_neon_cli_version                                                | Get neon cli version                     |         |
| TestNeonRPCBaseCalls::test_neon_get_solana_transaction_by_neon_transaction                 | Positive cases                           |         |
| TestNeonRPCBaseCalls::test_neon_get_solana_transaction_by_neon_transaction_list_of_tx      | List of sol tx                           |         |
| TestNeonRPCBaseCalls::test_neon_get_solana_transaction_by_neon_transaction_negative        | Negative cases                           |         |
| TestNeonRPCBaseCalls::test_neon_get_solana_transaction_by_neon_transaction_non_existent_tx | Non existent transaction, empty response |         |