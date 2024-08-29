# Overview

Verify basic opcodes

# Tests list

| Test case                                   | Description                                                      | XFailed |
|---------------------------------------------|------------------------------------------------------------------|---------|
| TestOpCodes::test_base_opcodes              | Execute base opcodes in contract                                 |         |
| TestOpCodes::test_stop                      | Execute stop opcode                                              |         |
| TestOpCodes::test_invalid_opcode            | Execute invalid opcode                                           |         |
| TestOpCodes::test_revert                    | Execute revert opcode                                            |         |
| TestBASEFEEOpcode::test_base_fee_call       | Verifies accuracy of base fee retrieval for call function        |         |
| TestBASEFEEOpcode::test_base_fee_trx_type_0 | Verifies accuracy of base fee retrieval for an old transaction   |         |
| TestBASEFEEOpcode::test_base_fee_trx_type_2 | Verifies accuracy of base fee retrieval for a type 2 transaction |         |
