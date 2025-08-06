// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Caller → Callee → InnerCallee

contract InnerCallee {
    uint256 public balance;
    bytes public storedData;


    receive() external payable {
        balance += msg.value;
    }

    function storeData(bytes memory data) public {
        storedData = abi.encodePacked(data, storedData);
    }

}

contract Callee {
    uint256 public balance;
    bytes public storedData;
    InnerCallee public innerCallee;

    constructor() {
        innerCallee = new InnerCallee();
    }

    receive() external payable {
        balance += msg.value;
    }

    function storeData(bytes memory data) public payable {
        (bool sent, ) = payable(address(innerCallee)).call{value: msg.value / 3}("");
        require(sent, "Send ETH to InnerCallee failed");

        storedData = abi.encodePacked(storedData, data);
        innerCallee.storeData(data);
    }
}


contract Caller {
    uint256 public balance;
    bytes public storedData;
    Callee public callee;

    constructor() {
        callee = new Callee();
    }

    receive() external payable {
        balance += msg.value;
    }

    function callAndChange(bytes memory data) public payable {
        storedData = abi.encodePacked(data, storedData);
        callee.storeData{value: msg.value / 2}(data);
    }
    function getCalleeAddress() public view returns (address) {
        return address(callee);
    }
    function getInnerCalleeAddress() public view returns (address) {
        return address(callee.innerCallee());
    }
}