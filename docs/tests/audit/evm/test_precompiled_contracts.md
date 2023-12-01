# Overview

Verify precompiled contracts work from contract and eth_call.
Supported precompiled contracts:

1. sha2_256
2. ecRecover
3. ripemd160
4. identify
5. blake2f

# Tests list

| Test case                                                | Description                                              | XFailed |
|----------------------------------------------------------|----------------------------------------------------------|---------|
| TestPrecompiledContracts::test_call_direct               | Call precompiled contract direct from eth_call           |         |
| TestPrecompiledContracts::test_call_via_contract         | Call precompiled contract from contract                  |         |
| TestPrecompiledContracts::test_staticcall_via_contract   | Call precompiled contract from contract via staticcall   |         |
| TestPrecompiledContracts::test_delegatecall_via_contract | Call precompiled contract from contract via delegatecall |         |
| TestPrecompiledContracts::test_call_via_send_trx         | Call precompiled contract from contract in transaction   |         |
| TestPrecompiledContracts::test_send_neon_without_data    | Send neon to precompiled contract                        |         |