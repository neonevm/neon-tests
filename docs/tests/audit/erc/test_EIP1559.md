# Overview

Test suite for EIP-1559

# Tests list

| Test case                                                                | Description                                                                                                                                | XFailed |
|--------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|---------|
| TestEIP1559::test_transfer_positive                                      | Verifies successful execution of a positive transfer using EIP-1559 transaction type, ensuring correct fee calculation and gas management. |         |
| TestEIP1559::test_deploy_positive                                        | Tests successful deployment of a contract using EIP-1559 transaction type with accurate fee calculation and gas management.                |         |
| TestEIP1559::test_contract_function_call_positive                        | Validates the invocation of a contract function with correct parameters using EIP-1559 transactions.                                       |         |
| TestEIP1559::test_transfer_negative                                      | Tests various negative scenarios for transfer transactions with incorrect parameters, ensuring proper error handling.                      |         |
| TestEIP1559::test_deploy_negative                                        | Evaluates various negative scenarios for contract deployment with incorrect parameters, ensuring proper error handling.                    |         |
| TestEIP1559::test_insufficient_funds                                     | Checks handling of transactions with insufficient funds, verifying appropriate error messages are returned.                                |         |
| TestRpcMaxPriorityFeePerGas::test_positive                               | Verifies correctness of retrieving max priority fee per gas using RPC methods in EIP-1559 context.                                         |         |
| TestRpcFeeHistory::test_positive_first_block                             | Tests retrieval of fee history from the first block, ensuring accurate data is returned.                                                   |         |
| TestRpcFeeHistory::test_positive_zero_block_count                        | Validates fee history retrieval with a zero block count, ensuring no data is returned.                                                     |         |
| TestRpcFeeHistory::test_positive_fewer_blocks_than_count                 | Checks fee history retrieval with fewer blocks than specified count, ensuring accurate data is returned.                                   |         |
| TestRpcFeeHistory::test_positive_earliest_block                          | Verifies accurate retrieval of fee history from the earliest block available.                                                              |         |
| TestRpcFeeHistory::test_positive_pending_block                           | Tests fee history retrieval for a pending block, ensuring correct handling of pending status.                                              |         |
| TestRpcFeeHistory::test_positive_max_blocks                              | Checks maximum number of blocks allowed for fee history retrieval, ensuring correct data handling.                                         |         |
| TestRpcFeeHistory::test_negative_cases                                   | Evaluates various negative cases for fee history retrieval, ensuring proper error codes are returned as expected.                          |         |
| TestRpcNeonMethods::test_neon_get_transaction_by_sender_nonce            | Verifies correct retrieval of transactions by sender nonce using Neon methods.                                                             |         |
| TestRpcNeonMethods::test_neon_get_solana_transaction_by_neon_transaction | Tests the retrieval of Solana transactions using Neon transaction data, ensuring accurate mapping.                                         |         |
| TestRpcNeonMethods::test_neon_get_transaction_receipt                    | Validates the retrieval of transaction receipts using Neon methods, ensuring accurate data is returned.                                    |         |
| TestRpcEthMethods::test_get_transaction_by_hash                          | Verifies correct retrieval of transactions by hash using Eth methods, ensuring data integrity.                                             |         |
| TestRpcEthMethods::test_get_transaction_by_block_hash_and_index          | Tests retrieval of transactions by block hash and index using Eth methods, ensuring accurate data is returned.                             |         |
| TestRpcEthMethods::test_get_transaction_by_block_number_and_index        | Checks retrieval of transactions by block number and index using Eth methods, ensuring accurate data is returned.                          |         |
| TestRpcEthMethods::test_get_block_by_hash                                | Validates retrieval of blocks by hash using Eth methods, ensuring accurate data is returned.                                               |         |
| TestRpcEthMethods::test_get_block_by_number                              | Tests retrieval of blocks by block number using Eth methods, ensuring accurate data is returned.                                           |         |
| TestRpcEthMethods::test_get_transaction_receipt                          | Checks retrieval of transaction receipts using Eth methods, ensuring accurate data is returned.                                            |         |
| TestAccessList::test_transfer                                            | Verifies proper handling of access list entries in transfer transactions, ensuring correct data management.                                |         |
| TestAccessList::test_deploy                                              | Tests correct application of access list entries during contract deployment, ensuring accurate transaction handling.                       |         |
