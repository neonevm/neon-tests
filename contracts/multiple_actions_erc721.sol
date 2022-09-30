pragma solidity >=0.7.0;

import "./erc721_for_metaplex.sol";

contract multipleActionsERC721 {
    uint256 data;
    ERC721ForMetaplex erc721;
    uint public lastTokenId;


    constructor() {
        erc721 = new ERC721ForMetaplex();
    }

    function balance(address who) public view returns (uint256) {
        return erc721.balanceOf(who);
    }

    function contractBalance() public view returns (uint256) {
        return erc721.balanceOf(address(this));
    }

    function mintTransfer(
        bytes32 seed,
        string memory uri,
        address transfer_to
    ) public {
        uint256 tokenId = erc721.mint(seed, address(this), uri);
        erc721.transferFrom(address(this), transfer_to, tokenId);
    }

    function transferMint(
        address transfer_to,
        bytes32 seed,
        uint256 tokenId,
        string memory uri
    ) public {
        erc721.transferFrom(address(this), transfer_to, tokenId);
        erc721.mint(seed, address(this), uri);
    }

    function mint(
        bytes32 seed,
        string memory uri
    ) public {
        lastTokenId = erc721.mint(seed, address(this), uri);
    }

    function mintMintTransferTransfer(
        bytes32 seed1,
        string memory uri1,
        bytes32 seed2,
        string memory uri2,
        address transfer_to1,
        address transfer_to2
    ) public {
        uint256 tokenId1 = erc721.mint(seed1, address(this), uri1);
        uint256 tokenId2 = erc721.mint(seed2, address(this), uri2);
        erc721.transferFrom(address(this), transfer_to1, tokenId1);
        erc721.transferFrom(address(this), transfer_to2, tokenId2);
    }
}