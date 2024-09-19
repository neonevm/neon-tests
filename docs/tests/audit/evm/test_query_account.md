# Overview

Validate QueryAccount library

# Tests list

| Test case                                | Description                                                                                         | XFailed |
|------------------------------------------|-----------------------------------------------------------------------------------------------------|---------|
| test_owner_positive                      | Verifies correct owner address retrieval for a Solana account                                       |         |
| test_owner_through_transaction_positive  | Verifies correct Solana address owner retrieval through a transaction (not function call)           |         |
| test_owner_negative_address_max_int      | Tests behavior of queryOwner function with maximum possible integer as Solana address               |         |
| test_length_positive                     | Checks if queryLength function returns correct data length for a Solana account                     |         |
| test_length_negative_address_max_int     | Tests behavior of queryLength function with maximum possible integer as Solana address              |         |
| test_lamports_positive                   | Ensures correct retrieval of lamports for a Solana account                                          |         |
| test_lamports_negative_address_max_int   | Tests behavior of queryLamports function with maximum possible integer as Solana address            |         |
| test_executable_true                     | Checks if queryExecutable function correctly identifies EVM loader-associated account as executable |         |
| test_executable_false                    | Verifies queryExecutable function correctly identifies regular Solana account as non-executable     |         |
| test_executable_negative_address_max_int | Tests behavior of queryExecutable function with maximum possible integer as Solana address          |         |
| test_rent_epoch_positive                 | Ensures correct retrieval of rent epoch for a Solana account                                        |         |
| test_rent_epoch_negative_address_max_int | Tests behavior of queryRentEpoch function with maximum possible integer as Solana address           |         |
| test_data_positive                       | Checks if queryData function returns correct data for an EVM loader-associated Solana account       |         |
| test_data_through_transaction_positive   | Checks if queryData function returns correct data through a transaction (not function call)         |         |
| test_data_negative_address_max_int       | Tests behavior of queryData function with maximum possible integer as Solana address                |         |
| test_data_negative_invalid_offset        | Verifies error handling of queryData function when providing an invalid offset                      |         |
| test_data_negative_length_zero           | Ensures queryData function returns an error when the provided length is zero                        |         |
| test_data_negative_invalid_length        | Tests error handling of queryData function when providing an invalid length                         |         |
