// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

import "../libraries/CarefulMath.sol";


contract BlockTimestamp is CarefulMath {
    event Result(uint256 block_timestamp);

    uint256 public a;
    uint public accrualBlockTimestamp;
    uint public accrualBlockNumber;

    struct Data {
        uint256 value1;
        uint256 value2;
    }

    mapping(uint256 => Data) public dataByTimestamp;

    event DataAdded(uint256 timestamp, uint256 value1, uint256 value2);

    constructor() {
        accrualBlockNumber = block.number;
        accrualBlockTimestamp = block.timestamp;
    }

    function getBlockTimestamp() public view returns (uint256) {
        return block.timestamp;
    }

    function logTimestamp() public {
        emit Result(block.timestamp);
    }

    function callIterativeTrx() public payable {
        uint256 timestamp_before = block.timestamp;
        for (uint256 i = 0; i < 800; i++) {
            a = a + block.timestamp;
        }
        emit Result(block.timestamp);
        uint256 timestamp_after = block.timestamp;

        require(timestamp_after == timestamp_before, "Timestamp changed during transaction execution");

    }

    function accrueInterest() public {
        uint currentBlockTimestamp = block.timestamp;
        uint accrualBlockTimestampPrior = accrualBlockTimestamp;

        (MathError mathErr, uint blockDelta) = subUInt(currentBlockTimestamp, accrualBlockTimestampPrior);
        require(mathErr == MathError.NO_ERROR, "calc block delta error");

        accrualBlockNumber = currentBlockTimestamp;
    }

    function addDataToMapping(uint256 _value1, uint256 _value2) public {
        uint256 currentTimestamp = block.timestamp % 1000000;
        for (uint256 i = 0; i < 20; i++) {
            Data memory newData = Data({
                value1: _value1,
                value2: _value2
            });
            dataByTimestamp[currentTimestamp] = newData;
            emit DataAdded(currentTimestamp, _value1, _value2);
            currentTimestamp = currentTimestamp + 1500;
        }
    }

    function getDataFromMapping(uint256 _timestamp) public view returns (uint256, uint256) {
        Data memory retrievedData = dataByTimestamp[_timestamp];
        return (retrievedData.value1, retrievedData.value2);
    }

}

contract BlockTimestampDeployer {
    BlockTimestamp public blockTimestamp;

    event Log(address indexed addr);

    constructor() {
        blockTimestamp = new BlockTimestamp();
        emit Log(address(blockTimestamp));
    }
}


contract BlockNumber is CarefulMath {
    event Log(address indexed sender, string message);
    event Result(uint256 block_number);

    bytes32[64] public b;


    uint256 public accrualBlockNumber;

    struct Data {
        uint256 value1;
        uint256 value2;
    }

    mapping(uint256 => Data) public dataByNumber;
    uint256 public a;

    event DataAdded(uint256 number, uint256 value1, uint256 value2);

    constructor() payable {
        accrualBlockNumber = block.number;
    }


    function getBlockNumber() public view returns (uint256) {
        return block.number;
    }

    function logBlockNumber() public {
        emit Result(block.number);
    }

    function callIterativeTrx() public payable {
        uint256 b = 1223;
        for (uint256 i = 0; i < 1000; i++) {
            a = a + block.number;
        }
        emit Result(block.number);
    }

    function addDataToMapping(uint256 _value1, uint256 _value2) public {
        uint256 currentNumber = block.number;
        for (uint256 i = 0; i < 5; i++) {
            Data memory newData = Data({
                value1: _value1,
                value2: _value2
            });

            dataByNumber[currentNumber] = newData;
            emit DataAdded(currentNumber, _value1, _value2);
            currentNumber = currentNumber + 1;
        }
    }

    function getDataFromMapping(uint256 _number) public view returns (uint256, uint256) {
        Data memory retrievedData = dataByNumber[_number];
        return (retrievedData.value1, retrievedData.value2);
    }


    function accrueInterest() public {
        uint currentBlockNumber = block.number;
        uint accrualBlockNumberPrior = accrualBlockNumber;

        (MathError mathErr, uint blockDelta) = subUInt(currentBlockNumber, accrualBlockNumberPrior);
        require(mathErr == MathError.NO_ERROR, "calc block delta error");

        accrualBlockNumber = currentBlockNumber;
    }


    function accrueInterestIterative() public {
        uint currentBlockNumber = block.number;
        uint accrualBlockNumberPrior = accrualBlockNumber;

        bytes memory result = new bytes(1000);
        for (uint256 i = 0; i < 1000; i++) {
            result[i] = "a";
        }

        (MathError mathErr, uint blockDelta) = subUInt(currentBlockNumber, accrualBlockNumberPrior);
        require(mathErr == MathError.NO_ERROR, "calc block delta error");

        accrualBlockNumber = currentBlockNumber;
    }
}