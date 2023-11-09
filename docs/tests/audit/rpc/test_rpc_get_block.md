# Overview

Tests for rpc get block

| Test case                                                          | Description                                | XFailed |
|--------------------------------------------------------------------|--------------------------------------------|---------|
| TestRpcGetBlock::test_eth_get_block_by_hash                        | Get block and check structure              |         |
| TestRpcGetBlock::test_eth_get_block_by_hash_with_incorrect_hash    | Try to get block with bad params           |         |
| TestRpcGetBlock::test_eth_get_block_by_hash_with_not_existing_hash | Try to get block with not exist hash       |         |
| TestRpcGetBlock::test_eth_get_block_by_number_via_numbers          | Try to get block by number                 |         |
| TestRpcGetBlock::test_eth_get_block_by_number_with_incorrect_data  | Try to get block by number with bad params |         |
| TestRpcGetBlock::test_eth_get_block_by_number_with_not_exist_data  | Try to get block by number with bad params |         |
| TestRpcGetBlock::test_eth_get_block_by_number_via_tags             | Get block by number with tags              |         |
