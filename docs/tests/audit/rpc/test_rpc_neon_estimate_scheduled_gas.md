# Overview

Tests for rpc estimate scheduled gas

| Test case                                                                                                 | Description                                                                      | XFailed   |
|-----------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------|-----------|
| TestNeonRPCEstimateScheduledGas::test_estimate_one_transaction                                            | Positive test, validate new field in response for scheduled tx                   |           |
| TestNeonRPCEstimateScheduledGas::test_send_multiple_transactions                                          | Positive test, check estimating multiply scheduled transactions                  |           |
| TestNeonRPCEstimateScheduledGas::test_one_of_multiply_transactions_failed                                 | Negative, one of transactions failed, wait error                                 |           |
| TestNeonRPCEstimateScheduledGas::test_no_transactions_in_request                                          | Negative, try to estimate request with no transactions                           |           |
| TestNeonRPCEstimateScheduledGas::test_send_value_greater_than_balance                                     | Negative, not enough balance                                                     | NDEV-3644 |
| TestNeonRPCEstimateScheduledGas::test_sender_has_no_sols                                                  | Positive, user has no sols                                                       |           |
| TestNeonRPCEstimateScheduledGas::test_no_function_in_called_contract                                      | Negative, no dedicated function in contract                                      |           |
| TestNeonRPCEstimateScheduledGas::test_wrong_chain_id                                                      | Negative, request to wrong chain                                                 |           |
| TestNeonRPCEstimateScheduledGas::test_wrong_format_field:fromAddress-invalid_from_address                 | Negative, check validation                                                       |           |
| TestNeonRPCEstimateScheduledGas::test_wrong_format_field:toAddress-invalid_to_address                     | Negative, check validation                                                       |           |
| TestNeonRPCEstimateScheduledGas::test_wrong_format_field:data-random_data                                 | Negative, check validation                                                       |           |
| TestNeonRPCEstimateScheduledGas::test_wrong_format_field:value-minus_100                                  | Negative, check validation                                                       |           |
| TestNeonRPCEstimateScheduledGas::test_estimate_with_preparatory_solana_transactions                       | Check estimation with preparatory solana transactions block                      |           |
| TestNeonRPCEstimateScheduledGas::test_estimate_transfer_trx_without_approval_in_preparatory_sol_trx_list  | Check estimation without preparatory solana transactions block when it is needed |           |
