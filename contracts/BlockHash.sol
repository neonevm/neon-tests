// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

contract BlockHashTest {
    event Added(bytes32 hash);

    function getCurrentValues() public payable returns (bytes32) {
        uint blockNumber = block.number;
        bytes32 blockHashNow = blockhash(blockNumber);
        emit Added(blockHashNow);
        return blockHashNow;
    }

    function getValues(uint number) public payable returns (bytes32) {
        bytes32 blockHash = blockhash(number);
        emit Added(blockHash);
        return blockHash;
    }
}