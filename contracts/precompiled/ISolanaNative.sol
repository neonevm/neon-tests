// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

interface ISolanaNative {
    function solanaAddress(address) external view returns(bytes32);

    function isSolanaUser(address) external view returns(bool);
}
