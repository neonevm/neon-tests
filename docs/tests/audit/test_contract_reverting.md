# Overview

Tests for check revert handling in different places

# Tests list

| Test case                                                               | Description                                                    | XFailed             |
|-------------------------------------------------------------------------|----------------------------------------------------------------|---------------------|
| TestContractReverting::test_constructor_raises_string_based_error | Get revert inside contract constructor                         |                     |
| TestContractReverting::test_constructor_raises_no_argument_error | Get revert inside contract constructor if not enough arguments |                     |
| TestContractReverting::test_method_raises_string_based_error | Get revert inside contract method and return string error      |                     |
| TestContractReverting::test_method_raises_trivial_error | Get revert inside contract method without error                |                     |
