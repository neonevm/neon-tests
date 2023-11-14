# Overview

Tests for rpc get transaction

| Test case                                                                        | Description                                                             | XFailed |
|----------------------------------------------------------------------------------|-------------------------------------------------------------------------|---------|
| TestRpcGetTransaction::test_eth_get_transaction_by_block_number_and_index        | Get block by number with tags and index                                 |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_block_hash_and_index          | Get block by hash with tags and index                                   |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_block_number_and_index_by_tag | Get block by hash with tags and index                                   |         |
| TestRpcGetTransaction::test_get_transaction_receipt_with_incorrect_hash          | Get receipt from random hash (eth & neon methods)                       |         |
| TestRpcGetTransaction::test_eth_get_transaction_count                            | Get transaction count                                                   |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_hash_negative                 | Get transaction by hash, negative cases                                 |         |
| TestRpcGetTransaction::test_eth_get_transaction_by_hash                          | Check method getTransactionByHash                                       |         |
| TestRpcGetTransaction::test_get_transaction_receipt                              | Check response structure for getTransactionReceipt (eth & neon methods) |         |
| TestRpcGetTransaction::test_get_transaction_receipt_when_hash_doesnt_exist       | Check getTransactionReceipt if tx hash not exist (eth & neon methods)   |         |
| TestRpcGetTransaction::test_eth_get_transaction_receipt_when_hash_doesnt_exist   | Non existent hash as param                                              |         |
| TestRpcGetTransaction::test_neon_get_transaction_by_sender_nonce_negative        | Negative cases with posible error checkes                               |         |
| TestRpcGetTransaction::test_neon_get_transaction_by_sender_nonce_plus_one        | Request nonce+1, which is not exist                                     |         |
| TestRpcGetTransaction::test_neon_get_transaction_by_sender_nonce                 | Positive cases                                                          |         |
