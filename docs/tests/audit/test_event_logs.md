# Overview

Tests for check transfer tokens from solana->neon and neon->solana

# Tests list

| Test case                                             | Description                                           | XFailed |
|-------------------------------------------------------|-------------------------------------------------------|---------|
| TestLogs::test_non_args_event                         | Check event without arguments                         |         |
| TestLogs::test_all_types_args_event                   | Check event with different types args                 |         |
| TestLogs::test_indexed_args_event                     | Check event with indexed args                         |         |
| TestLogs::test_non_indexed_args_event                 | Check event with non-indexed args                     |         |
| TestLogs::test_unnamed_args_event                     | Check event with non named argument                   |         |
| TestLogs::test_big_args_count                         | Check event with big arguments                        |         |
| TestLogs::test_several_events_in_one_trx              | Check several events in one transaction               |         |
| TestLogs::test_many_the_same_events_in_one_trx        | Check several the same events in one transaction      |         |
| TestLogs::test_event_logs_deleted_if_trx_was_canceled | Check that logs not exist if transaction cancelled    |         |
| TestLogs::test_nested_calls_with_revert               | Check that logs exist if nested contract was reverted |         |
