# Overview

Test for ERC721: Verify integration with Metaplex for NFT collections

# Tests list

| Test case                                                                         | Description                                                                   | XFailed |
|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------|---------|
| TestERC721::test_mint_with_used_seed                                              | Check that we can't mint with old seed                                        |         |
| TestERC721::test_name                                                             | Get name                                                                      |         |
| TestERC721::test_symbol                                                           | Get symbol                                                                    |         |
| TestERC721::test_balance_of                                                       | Check balanceOf method                                                        |         |
| TestERC721::test_owner_of                                                         | Get owner                                                                     |         |
| TestERC721::test_tokenURI                                                         | Get tokenUri                                                                  |         |
| TestERC721::test_transfer_from_with_approval                                      | Check transfer work with approval                                             |         |
| TestERC721::test_safe_transfer_from_with_data                                     | Verify method safeTransferFrom with data                                      |         |
| TestERC721::test_safe_transfer_from_to_invalid_contract                           | Verify method safeTransferFrom doesn't work to invalid contract               |         |
| TestERC721::test_set_approval_for_all                                             | Verify method setApprovalForAll work                                          |         |
| TestERC721::test_transfer_solana_from                                             | Check method transferSolanaFrom                                               |         |
| TestMultipleActionsForERC721::test_transfer_mint                                  | Check transfer -> mint in one transaction                                     |         |
| TestMultipleActionsForERC721::test_mint_mint_transfer_transfer                    | Check mint -> mint -> transfer -> transfer in one transaction                 |         |
| TestMultipleActionsForERC721::test_mint_mint_transfer_transfer_different_accounts | Check mint -> mint -> transfer -> transfer to dif accounts in one transaction |         |
| TestERC721Extensions::test_erc_4907_rental_nft                                    | Check ERC4907 for rent NFT                                                    |         |
| TestERC721Extensions::test_erc_2981_default_royalty                               | Check ERC2981 and check default royalty                                       |         |
| TestERC721Extensions::test_erc_2981_token_royalty                                 | Check ERC2981 and check custom royalty                                        |         |