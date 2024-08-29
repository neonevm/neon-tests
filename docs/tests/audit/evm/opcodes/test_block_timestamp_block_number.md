# Overview

Check timestamp and block number opcodes.

# Tests list

| Test case                                                                  | Description                                    | XFailed |
|----------------------------------------------------------------------------|------------------------------------------------|---------|
| TestBlockTimestampAndNumber::test_block_timestamp_call                     | Check contract return timestamp                |         |
| TestBlockTimestampAndNumber::test_block_timestamp_simple_trx               | Check simple transaction with timestamp        |         |
| TestBlockTimestampAndNumber::test_block_timestamp_iterative                | Check iterative transaction with timestamp     |         |
| TestBlockTimestampAndNumber::test_block_timestamp_constructor              | Check timestamp in constructor                 |         |
| TestBlockTimestampAndNumber::test_block_timestamp_in_mapping               | Check timestamp as a key in mapping            |         |
| TestBlockTimestampAndNumber::test_contract_deploys_contract_with_timestamp | Check contract deploys contract with timestamp |         |
| TestBlockTimestampAndNumber::test_block_number_call                        | Check contract return block number             |         |
| TestBlockTimestampAndNumber::test_block_number_simple_trx                  | Check simple transaction with block number     |         |
| TestBlockTimestampAndNumber::test_block_number_iterative                   | Check iterative transaction with block number  |         |
| TestBlockTimestampAndNumber::test_block_number_constructor                 | Check block number in constructor              |         |
| TestBlockTimestampAndNumber::test_block_number_in_mapping                  | Check block number as a key in mapping         |         |
