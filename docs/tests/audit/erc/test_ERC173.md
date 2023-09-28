# Overview

Test for ERC-173: Contract Ownership Standard

# Tests list

| Test case                                                                   | Description                                  | XFailed |
|-----------------------------------------------------------------------------|----------------------------------------------|---------|
| TestERC173ContractOwnershipStandard::test_ownership_transfer                | Check that ownership changes                 |         |
| TestERC173ContractOwnershipStandard::test_only_owner_can_transfer_ownership | Check that only owner could change ownership |         |
| TestERC173ContractOwnershipStandard::test_renounce_ownership                | Renounce ownership                           |         |
| TestERC173ContractOwnershipStandard::test_contract_call_ownership_transfer  | Change ownership via contract                |         |