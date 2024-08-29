pragma solidity >=0.4.0;

/**
 * @title Storage
 * @dev Store & retrieve value in a variable
 */
contract Storage {
    uint256 number;
    uint256 numberTwo;
    uint256 time;
    uint256[] public values;

    function store(uint256 num) public {
        number = num;
        values = [number];
    }

    function retrieve() public view returns (uint256) {
        return number;
    }

    function retrieveSenderBalance() public view returns (uint256) {
        return msg.sender.balance;
    }

   function storeSumOfNumbers(uint256 num1, uint256 num2) public view returns (uint256) {
        if (number == 101) {
            num1 = 0;
        }
        if (numberTwo == 103) {
            num2 = 5;
        }
        return num1 + num2;
    }

    function at(address _addr) public view returns (bytes memory) {
        return _addr.code;
    }

    function storeBlock() public {
        number = block.number;
        values = [number];
    }

    function storeBlockTimestamp() public returns (uint256) {
        number = block.timestamp;
        values = [number];
        return block.timestamp;
    }

    function storeBlockInfo() public {
        number = block.number;
        time = block.timestamp;
        values = [number, time];
    }

    function returnDoubledNumber(uint256 num) public view returns (uint256) {
        if (number == 102) {
            num = 10;
        }
        return num * 2;
    }
}

contract StorageMultipleVars {
    string public data = "test";
    uint256 public constant number = 1;
    uint256 public notSet;

    function setData(string memory _data) public {
        data = _data;
    }
}
