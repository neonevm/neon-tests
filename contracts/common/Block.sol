// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;


contract BlockTimestamp {
    event Result(uint256 block_timestamp);
    uint256 public a;
    uint256 public initial_block_timestamp;

    struct Data {
        string info;
        uint256 value;
    }
    mapping(uint256 => Data) public dataByTimestamp;
    event DataAdded(uint256 timestamp, string info, uint256 value);

    constructor() {
        initial_block_timestamp = block.timestamp;
    }

    function getBlockTimestamp() public view returns (uint256) {
        return block.timestamp;
    }

    function logTimestamp() public {
        emit Result(block.timestamp);
    }

    function callTimestampIterativeTrx() public payable {
        for (uint256 i = 0; i < 2000; i++) {
            a = a + block.timestamp;
        }
        emit Result(block.timestamp);
    }

    function addDataToMapping(string memory _info, uint256 _value) public {
        uint256 currentTimestamp = block.timestamp;
        for (uint256 i = 0; i < 5; i++) {
            Data memory newData = Data({
                info: _info,
                value: _value
            });

            dataByTimestamp[currentTimestamp] = newData;
            emit DataAdded(currentTimestamp, _info, _value);
            currentTimestamp = currentTimestamp + 1;
        }
    }

    function getDataFromMapping(uint256 _timestamp) public view returns (string memory, uint256) {
        Data memory retrievedData = dataByTimestamp[_timestamp];
        return (retrievedData.info, retrievedData.value);
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


contract BlockNumber {
    event Log(address indexed sender, string message);
    event Result(uint256 block_number);
    uint256 public a;

    uint256 public initial_block_number;

    struct Data {
        string info;
        uint256 value;
    }
    mapping(uint256 => Data) public dataByNumber;
    event DataAdded(uint256 number, string info, uint256 value);

    constructor() payable {
        initial_block_number = block.number;
    }


    function getBlockNumber() public view returns (uint256) {
        return block.number;
    }

    function logBlockNumber() public {
        emit Result(block.number);
    }

    function callBlockNumberIterativeTrx() public payable {
        for (uint256 i = 0; i < 2000; i++) {
            a = a + block.number;
        }
        emit Result(block.number);
    }

    function addDataToMapping(string memory _info, uint256 _value) public {
        uint256 currentNumber = block.number;
        for (uint256 i = 0; i < 5; i++) {
            Data memory newData = Data({
                info: _info,
                value: _value
            });

            dataByNumber[currentNumber] = newData;
            emit DataAdded(currentNumber, _info, _value);
            currentNumber = currentNumber + 1;
        }
    }

    function getDataFromMapping(uint256 _number) public view returns (string memory, uint256) {
        Data memory retrievedData = dataByNumber[_number];
        return (retrievedData.info, retrievedData.value);
    }
}