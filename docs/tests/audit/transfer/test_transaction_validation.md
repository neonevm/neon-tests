# Overview

Tests for transfer transactions validation

# Tests list

| Test case                                                              | Description                                         | XFailed   |
|------------------------------------------------------------------------|-----------------------------------------------------|-----------|
| TestTransactionsValidation::test_generate_bad_sign                     | Send transaction with invalid sign and got an error |           |
| TestTransactionsValidation::test_send_underpriced_transaction          | Send transaction with not enough gas_price          |           |
| TestTransactionsValidation::test_send_too_big_transaction              | Send a big transaction 256*1024 in data             |           |
| TestTransactionsValidation::test_send_transaction_with_small_gas_price | Send a transaction with small gas price             | NDEV-2386 |
| TestTransactionsValidation::test_big_memory_value                      | Check memory overflow                               |           |