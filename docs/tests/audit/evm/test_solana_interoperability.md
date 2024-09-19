# Overview

Check Solana interoperability

# Tests list

| Test case                                                             | Description                                                                   | XFailed |
|-----------------------------------------------------------------------|-------------------------------------------------------------------------------|---------|
| TestSolanaInteroperability::test_counter_execute_with_get_return_data | Execute Counter program and get return data                                   |         |
| TestSolanaInteroperability::test_counter_with_seed                    | Execute Counter program with seed                                             |         |
| TestSolanaInteroperability::test_counter_execute                      | Execute Counter program and check response                                    |         |
| TestSolanaInteroperability::test_counter_batch_execute                | Execute 10 Counter programs in batch                                          |         |
| TestSolanaInteroperability::test_transfer_with_pda_signature          | Execute program for Transfer tokens                                           |         |
| TestSolanaInteroperability::test_transfer_tokens_with_ext_authority   | Execute program for Tokens                                                    |         |
| TestSolanaInteroperability::test_gas_estimate_for_wsol_transfer       | Transfer wsol and check that gas estimation doesn't depend of transfer amount |         |
