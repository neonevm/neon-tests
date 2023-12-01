pragma solidity >=0.4.0;

/**
 * @title Storage
 * @dev Store & retrieve value in a variable
 */
contract Storage {
    uint256 number;

    /**
     * @dev Store value in variable
     * @param num value to store
     */
    function store(uint256 num) public {
        number = num;
    }

    /**
     * @dev Return value
     * @return value of 'number'
     */
    function retrieve() public view returns (uint256) {
        return number;
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