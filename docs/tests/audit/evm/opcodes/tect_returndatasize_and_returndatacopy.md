# Overview

Verify opcodes: returndatasize and returndatacopy

# Tests list

| Test case                                                                     | Description                                                        | XFailed |
|-------------------------------------------------------------------------------|--------------------------------------------------------------------|---------|
| TestReturnDataSizeAndCopyOpcodes::test_returndatasize                         | Get data size from contract via returndata opcode                  |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatacopy_for_call                | Get data from contract via returndata opcode with call in contract |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatacopy_for_delegatecall        | Get data from contract via returndata opcode with delegatecall     |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatacopy_for_staticcall          | Get data from contract via returndata opcode with staticcall       |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatasize_for_create              | Get data from contract via returndata opcode inside CREATE         |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatasize_for_create2             | Get data from contract via returndata opcode inside CREATE2        |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatacopy_for_create_with_revert  | Get data from contract via returndata opcode on revert in create   |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatacopy_for_create2_with_revert | Get data from contract via returndata opcode on revert in create2  |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatacopy_with_different_params   | Get data from contract via returndata opcode with different params |         |
| TestReturnDataSizeAndCopyOpcodes::test_returndatacopy_with_invalid_params     | Get data from contract via returndata opcode with invalid params   |         |
