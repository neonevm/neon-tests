# Overview

Tests for batch operations

# Tests list

| Test case                                                             | Description                                                                                   | XFailed |
|-----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|---------|
| TestBatchOperations::test_batch_operations_same_function              | sends a batch operation request with 100 calls to the same function with different parameters |         |
| TestBatchOperations::test_batch_operations_different_functions        | sends a batch operation request with a few calls to different functions                       |         |
| TestBatchOperations::test_batch_operations_negative                   | sends a batch operation request with a few calls with invalid parameters                      |         |
| TestBatchOperations::test_batch_operations_positive_and_negative_mix  | sends a batch operation request with a mix of positive and calls to different functions       |         |
