// SPDX-License-Identifier: MIT

pragma solidity >=0.7.0;

import "../libraries/external/QueryAccount.sol";

contract QueryAccountCaller {

    event QueryResultUint256(bool success, uint256 result);
    event QueryResultBytes(bool success, bytes result);

    function queryOwner(uint256 solana_address) external returns (bool, uint256) {
        (bool success, uint256 result) = QueryAccount.owner(solana_address);
        emit QueryResultUint256(success, result);
        return (success, result);
    }

    function queryLength(uint256 solana_address) external view returns (bool, uint256) {
        (bool success, uint256 result) = QueryAccount.length(solana_address);
        return (success, result);
    }

    function queryLamports(uint256 solana_address) external view returns (bool, uint256) {
        (bool success, uint256 result) = QueryAccount.lamports(solana_address);
        return (success, result);
    }

    function queryExecutable(uint256 solana_address) external view returns (bool, bool) {
        (bool success, bool result) = QueryAccount.executable(solana_address);
        return (success, result);
    }

    function queryRentEpoch(uint256 solana_address) external view returns (bool, uint256) {
        (bool success, uint256 result) = QueryAccount.rent_epoch(solana_address);
        return (success, result);
    }

    function queryData(uint256 solana_address, uint64 offset, uint64 len) external returns (bool, bytes memory) {
        (bool success, bytes memory result) = QueryAccount.data(solana_address, offset, len);
        emit QueryResultBytes(success, result);
        return (success, result);
    }
}
