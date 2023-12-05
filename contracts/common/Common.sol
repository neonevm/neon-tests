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

contract BunchActions {

    function setNumber(address[] memory addresses, uint256[] memory _numbers) public {
        for (uint256 i = 0; i < addresses.length; ++i) {
             Common(addresses[i]).setNumber(_numbers[i]);
        }
    }
}


contract MappingActions {
    mapping(uint256 => string) public stringMapping;

    // Function to replace n values in the mapping
    function replaceValues(uint256 n) external {

        for (uint256 i = 0; i < n; i++) {
            stringMapping[i] = "UpdatedString";
        }

    }
}