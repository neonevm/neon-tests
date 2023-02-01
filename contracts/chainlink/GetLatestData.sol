// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./ChainlinkOracle.sol";

contract GetLatestData {
    function getLatestData(address addr)
        public
        view
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        )
    {
        ChainlinkOracle chainlink = ChainlinkOracle(addr);
        return chainlink.latestRoundData();
    }

    function getDecimals(address addr) public view returns (uint8) {
        ChainlinkOracle chainlink = ChainlinkOracle(addr);
        return chainlink.decimals();
    }

    function getDescription(address addr) public view returns (string memory) {
        ChainlinkOracle chainlink = ChainlinkOracle(addr);
        return chainlink.description();
    }

    function getVersion(address addr) public view returns (uint256) {
        ChainlinkOracle chainlink = ChainlinkOracle(addr);
        return chainlink.version();
    }
}
