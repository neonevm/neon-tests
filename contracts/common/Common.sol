pragma solidity ^0.8.12;

contract Common {
    string public text = "hello";
    uint256 public number = 55;


    function getText() public view returns (string memory) {
        return text;
    }

    function setText(string memory _text) public {
        text = _text;
    }

    function getNumber() public view returns (uint256) {
        return number;
    }

    function setNumber(uint256 _number) public {
        number = _number;
    }


}

contract CommonCaller {
    Common public myCommon;

    constructor(address commonAddress) {
        myCommon = Common(commonAddress);
    }

    function getNumber() public view returns (uint256) {
         return myCommon.getNumber();
    }
}