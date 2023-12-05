# Overview

Verify EIP-1052: EXTCODEHASH opcode

# Tests list

| Test case                                                                     | Description                                          | XFailed |
|-------------------------------------------------------------------------------|------------------------------------------------------|---------|
| TestChainIdDependentOpcodes::test_chain_id_sol                  | Call 'chainid' opcode in sol chain contract          |         |
| TestChainIdDependentOpcodes::test_chain_id_neon                  | Call 'chainid' opcode in neon chain contract         |         |
| TestChainIdDependentOpcodes::test_balance_by_sol_contract     | Call 'balance' opcode from sol-native chain contract |         |
| TestChainIdDependentOpcodes::test_balance_by_neon_contract     | Call 'balance' opcode from neon-native chain contract  |         |
