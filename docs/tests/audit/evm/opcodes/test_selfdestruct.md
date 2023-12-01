# Overview

Verify SELFDESTRUCT opcode

# Tests list

| Test case                                                                              | Description                                          | XFailed |
|----------------------------------------------------------------------------------------|------------------------------------------------------|---------|
| TestSelfDestructOpcode::test_destroy                                                   | Normal contract destroy                              |         |
| TestSelfDestructOpcode::test_destroy_contract_with_contract_address_as_target          | Normal contract destroy from contract                |         |
| TestSelfDestructOpcode::test_destroy_contract_and_sent_neons_to_contract               | Normal destroy and send neon                         |         |
| TestSelfDestructOpcode::test_destroy_contract_by_call_from_second_contract             | Normal destroy and from contract call                |         |
| TestSelfDestructOpcode::test_destroy_contract_and_sent_neon_from_contract_in_one_trx   | Destroy and send neon from in one transaction        |         |
| TestSelfDestructOpcode::test_sent_neon_from_contract_and_destroy_contract_in_one_trx   | Send and destroy in one transaction                  |         |
| TestSelfDestructOpcode::test_destroy_contract_and_sent_neon_to_contract_in_one_trx     | Destroy and send neon to contract in one transaction |         |
| TestSelfDestructOpcode::test_destroy_contract_2_times_in_one_trx                       | Execute opcode twice                                 |         |
| TestSelfDestructOpcode::test_destroy_contract_via_delegatecall                         | Destroy in delegatecall                              |         |
| TestSelfDestructOpcode::test_destroy_contract_via_delegatecall_and_create_new_contract | Destroy in delegatecall and create new contract      |         |
