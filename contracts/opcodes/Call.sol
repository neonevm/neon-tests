// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Caller {
    string public text = "base text";
    address public sender_in_called_contract;

    event CallResult(bool success, bytes data);
    event LogCounterValue(uint256 counter_value);

    event LogSenderInCalledContract(address sender_in_called_contract);


    function callSetText(address _contractAddress, string memory _text) public {
        bytes memory data = abi.encodeWithSignature("setText(string)", _text);
        (bool success, bytes memory returnData) = _contractAddress.call(data);
        emit CallResult(success, returnData);
    }

    function callGetText(address _contractAddress) public returns (string memory) {
        bytes memory data = abi.encodeWithSignature("getText()");
        (bool success, bytes memory returnData) = _contractAddress.call(data);
        require(success, "CALL failed");

        string memory _text = abi.decode(returnData, (string));
        return _text;
    }

    function callSetTextReturnSenderAddr(address _contractAddress, string memory _text) public {
        bytes memory data = abi.encodeWithSignature("setTextReturnSenderAddr(string)", _text);
        (bool success, bytes memory returnData) = _contractAddress.call(data);
        address senderInCalledContract = abi.decode(returnData, (address));
        emit LogSenderInCalledContract(senderInCalledContract);
        emit CallResult(success, returnData);
    }

    function callSetTextAndSendValue(address _contractAddress, string memory _text) public payable {
        bytes memory data = abi.encodeWithSignature("setTextAndReceiveValue(string)", _text);
        (bool success, bytes memory returnData) = _contractAddress.call{value: msg.value}(data);
        emit CallResult(success, returnData);
    }


    function staticcallGetText(address _contractAddress) public view returns (string memory) {
        bytes memory data = abi.encodeWithSignature("getText()");
        (bool success, bytes memory returnData) = _contractAddress.staticcall(data);

        require(success, "CALL failed");
        string memory _text = abi.decode(returnData, (string));
        return _text;
    }

    function staticcallSetText(address _contractAddress, string memory _text) public {
        bytes memory data = abi.encodeWithSignature("setText(string)", _text);

        (bool success, bytes memory returnData) = _contractAddress.staticcall(data);
        emit CallResult(success, returnData);
    }

    function delegateCallSetText(address _contractAddress, string memory _text) public {
        bytes memory data = abi.encodeWithSignature("setText(string)", _text);
        (bool success, bytes memory returnData) = _contractAddress.delegatecall(data);
        emit CallResult(success, returnData);
    }

    function delegatecallSetTextReturnSenderAddr(address _contractAddress, string memory _text) public {
        bytes memory data = abi.encodeWithSignature("setTextReturnSenderAddr(string)", _text);
        (bool success, bytes memory returnData) = _contractAddress.delegatecall(data);
        address senderInCalledContract = abi.decode(returnData, (address));
        emit LogSenderInCalledContract(senderInCalledContract);
        emit CallResult(success, returnData);
    }
}