// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";
import "../libraries/Utils.sol";

contract ChainlinkOracle is AggregatorV3Interface {
    uint8 public _decimals;
    uint256 public feedAddress;
    string public _description;
    uint256 public _version;
    uint32 private historicalLength;

    constructor(bytes32 _feedAddress) {
        feedAddress = uint256(_feedAddress);

        Utils.Header memory header = Utils.getHeader(feedAddress);
        _version = header.version;
        _description = header.description;
        _decimals = header.decimals;
        // Save historical ringbuffer length for future use.
        historicalLength = Utils.getHistoricalLength(
            feedAddress,
            header.liveLength
        );
    }

    function getRoundData(uint80 _roundId)
        external
        view
        override
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        )
    {
        Utils.Round memory round = Utils.getRoundbyId(
            feedAddress,
            uint32(_roundId),
            historicalLength
        );

        return (
            round.roundId,
            round.answer,
            round.timestamp,
            round.timestamp,
            round.roundId
        );
    }

    function latestRoundData()
        external
        view
        override
        returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        )
    {
        Utils.Round memory round = Utils.getLatestRound(feedAddress);

        return (
            round.roundId,
            round.answer,
            round.timestamp,
            round.timestamp,
            round.roundId
        );
    }

    function decimals() external view override returns (uint8) {
        return _decimals;
    }

    function description() external view override returns (string memory) {
        return _description;
    }

    function version() external view override returns (uint256) {
        return _version;
    }
}
