# Overview

Test for ERC721: Verify integration with Metaplex for NFT collections

# Tests list

| Test case                                                                         | Description                                                                   | XFailed   |
|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------|-----------|
| TestERC721::test_mint                                                             | Check that we can mint new token and it will registered in Metaplex           |           |
| TestERC721::test_mint_with_used_seed                                              | Check that we can't mint with old seed                                        |           |
| TestERC721::test_mint_can_all                                                     | Check that anyone could mint                                                  |           |
| TestERC721::test_mint_incorrect_address                                           | Check that can't mint for bad address                                         |           |
| TestERC721::test_mint_no_enough_gas                                               | Can't mint if not enough gas                                                  |           |
| TestERC721::test_name                                                             | Get name                                                                      |           |
| TestERC721::test_symbol                                                           | Get symbol                                                                    |           |
| TestERC721::test_balanceOf                                                        | Check balanceOf method                                                        |           |
| TestERC721::test_balanceOf_incorrect_address                                      | Check balanceOf method with bad data                                          |           |
| TestERC721::test_ownerOf                                                          | Get owner                                                                     |           |
| TestERC721::test_ownerOf_incorrect_token                                          | Get owner from invalid token                                                  |           |
| TestERC721::test_tokenURI                                                         | Get tokenUri                                                                  |           |
| TestERC721::test_tokenURI_incorrect_token                                         | Get tokenUri from invalid token                                               |           |
| TestERC721::test_transferFrom                                                     | Check transfer work                                                           |           |
| TestERC721::test_transferFrom_not_token_owner                                     | Check transfer doesn't work with bad owner                                    |           |
| TestERC721::test_transferFrom_incorrect_owner                                     | Check transfer doesn't work with invalid owner                                |           |
| TestERC721::test_transferFrom_incorrect_token                                     | Check transfer doesn't work with bad token                                    |           |
| TestERC721::test_transferFrom_incorrect_address_from                              | Check transfer doesn't work with incorrect from field                         |           |
| TestERC721::test_transferFrom_incorrect_address_to                                | Check transfer doesn't work with incorrect to field                           |           |
| TestERC721::test_transferFrom_no_enough_gas                                       | Check transfer doesn't work not enough gas                                    |           |
| TestERC721::test_transferFrom_with_approval                                       | Check transfer work with approval                                             |           |
| TestERC721::test_approve_for_owner                                                | Approve from bad user                                                         |           |
| TestERC721::test_approve_incorrect_token                                          | Try to approve invalid token                                                  |           |
| TestERC721::test_approve_incorrect_address                                        | Try to approve incorrect address                                              |           |
| TestERC721::test_approve_no_owner                                                 | Try to approve not owner                                                      |           |
| TestERC721::test_approve_no_enough_gas                                            | Try to approve with not enough gas                                            |           |
| TestERC721::test_safeTransferFrom_to_user                                         | Verify method safeTransferFrom work to user                                   |           |
| TestERC721::test_safeTransferFrom_to_contract                                     | Verify method safeTransferFrom work to contract                               |           |
| TestERC721::test_safeTransferFrom_with_data                                       | Verify method safeTransferFrom with data                                      |           |
| TestERC721::test_safeTransferFrom_to_invalid_contract                             | Verify method safeTransferFrom doesn't work to invalid contract               |           |
| TestERC721::test_safeMint_to_user                                                 | Verify method safeMint work to user                                           |           |
| TestERC721::test_safeMint_to_contract                                             | Verify method safeMint work to contract                                       |           |
| TestERC721::test_safeMint_with_data                                               | Verify method safeMint with data                                              |           |
| TestERC721::test_safeMint_to_invalid_contract                                     | Verify method safeMint doesn't work to invalid contract                       |           |
| TestERC721::test_setApprovalForAll                                                | Verify method setApprovalForAll work                                          |           |
| TestERC721::test_setApprovalForAll_incorrect_address                              | Verify method setApprovalForAll raise error for incorrect address             |           |
| TestERC721::test_setApprovalForAll_approve_to_caller                              | Verify method setApprovalForAll raise error on caller approve                 |           |
| TestERC721::test_setApprovalForAll_no_enough_gas                                  | Verify method setApprovalForAll raise error when not enough gas               |           |
| TestERC721::test_isApprovedForAll                                                 | Verify method isApprovedForAll work                                           |           |
| TestERC721::test_isApprovedForAll_incorrect_owner_address                         | Verify method isApprovedForAll raise error for invalid owner                  |           |
| TestERC721::test_isApprovedForAll_incorrect_operator_address                      | Verify method isApprovedForAll raise error for invalid operator               |           |
| TestERC721::test_getApproved                                                      | Verify method getApproved work                                                |           |
| TestERC721::test_getApproved_incorrect_token                                      | Verify method getApproved raise error for incorrect token                     |           |
| TestERC721::test_transferSolanaFrom                                               | Check method transferSolanaFrom                                               | NDEV-1333 |
| TestMultipleActionsForERC721::test_mint_transfer                                  | Check mint -> transfer in one transaction                                     |           |
| TestMultipleActionsForERC721::test_transfer_mint                                  | Check transfer -> mint in one transaction                                     |           |
| TestMultipleActionsForERC721::test_mint_mint_transfer_transfer                    | Check mint -> mint -> transfer -> transfer in one transaction                 |           |
| TestMultipleActionsForERC721::test_mint_mint_transfer_transfer_different_accounts | Check mint -> mint -> transfer -> transfer to dif accounts in one transaction |           |
| TestERC721Extensions::test_ERC4907_rental_nft                                     | Check ERC4907 for rent NFT                                                    |           |
| TestERC721Extensions::test_ERC2981_default_royalty                                | Check ERC2981 and check default royalty                                       |           |
| TestERC721Extensions::test_ERC2981_token_royalty                                  | Check ERC2981 and check custom royalty                                        |           |