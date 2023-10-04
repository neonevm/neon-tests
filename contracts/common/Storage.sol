pragma solidity ^0.8.12;

contract Storage {
    string public data = "test";
    uint256 constant public number = 1;
    uint256 public notSet;

    function setData(string memory _data) public  {
        data = _data;
    }
}