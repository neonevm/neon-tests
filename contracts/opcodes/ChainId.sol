// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

contract ChainId {
    event Added(bytes32 hash);

    function getCurrentValues() public view returns (uint256) {
        uint256 id;
        assembly {
            id := chainid()
        }
        return id;
    }

}