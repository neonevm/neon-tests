# Overview

Tests for rpc send raw transaction

| Test case                                                          | Description                                                 | XFailed   |
|--------------------------------------------------------------------|-------------------------------------------------------------|-----------|
| TestNeonRPCSendRAWTransaction::test_two_transactions_in_params     | Negative, send 2 transaction in 1 request, wait error       |           |
| TestNeonRPCSendRAWTransaction::test_repeat_call_with_same_trx_hash | Negative, send transaction twice with same hash, wait error | NDEV-3609 |
| TestNeonRPCSendRAWTransaction::test_no_tree_account_for_trx        | Negative, not created tree account, wait error              |           |
| TestNeonRPCSendRAWTransaction::test_bad_chain_id_url               | Negative, wrong chain id                                    |           |
| TestNeonRPCSendRAWTransaction::test_bad_empty_hash_of_trx          | Negative, empty hash in params                              |           |
| TestNeonRPCSendRAWTransaction::test_bad_hash_of_trx:empty_param    | Negative, send empty string in param                        |           |
| TestNeonRPCSendRAWTransaction::test_bad_hash_of_trx:broken_param   | Negative, send invalid string in param                      |           |
|
