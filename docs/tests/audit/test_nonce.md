# Overview

Verify mempool work and how proxy handles it

# Tests list

| Test case                                                           | Description                                                                       | XFailed |
|---------------------------------------------------------------------|-----------------------------------------------------------------------------------|---------|
| TestNonce::test_get_receipt_sequence                                | Check receipts if transactions sended  in sequence                                |         |
| TestNonce::test_reverse_sequence                                    | Check receipts if transactions sended in reverse (big nonce before small)         |         |
| TestNonce::test_random_sequence                                     | Check receipts if transactions sended in random order                             |         |
| TestNonce::test_send_transaction_with_low_nonce_after_several_high  | Check that transaction with a higher nonce is waiting for its turn in the mempool |         |
| TestNonce::test_send_transaction_with_low_nonce_after_high          | Check that transaction with a higher nonce is waiting for its turn in the mempool |         |
| TestNonce::test_send_transaction_with_the_same_nonce_and_lower_gas  | Check that transaction with smaller gas not replaced                              |         |
| TestNonce::test_send_transaction_with_the_same_nonce_and_higher_gas | Check that transaction with higher gas replace tx                                 |         |