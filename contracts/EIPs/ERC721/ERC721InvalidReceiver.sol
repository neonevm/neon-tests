// SPDX-License-Identifier: MIT

pragma solidity >=0.8.0;

contract ERC721Receiver {
    function someFunction(
        address,
        address,
        uint256,
        bytes calldata data
    ) external returns (bytes4) {
        return
            bytes4(
                keccak256("onERC721Received(address,address,uint256,bytes)")
            );
    }
}
