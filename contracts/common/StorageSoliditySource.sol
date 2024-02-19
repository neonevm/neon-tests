pragma solidity >=0.4.0;

/**
 * @title Storage
 * @dev Store & retrieve value in a variable
 */
contract Storage {
    uint256 number;

    /**
     * @dev Stores value in variable
     * @param num value to store
     */
    function store(uint256 num) public {
        number = num;
    }

    /**
     * @dev Returns value
     * @return value of 'number'
     */
    function retrieve() public view returns (uint256) {
        return number;
    }

    /**
     * @dev Returns code for given address
     * @return value of '_addr.code'
     */
    function at(address _addr) public view returns (bytes memory) {
        return _addr.code;
    }
}

contract StorageMultipleVars {
    string public data = "test";
    uint256 constant public number = 1;
    uint256 public notSet;

    function setData(string memory _data) public  {
        data = _data;
    }
}