// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

//Tree of execution:

    //ChainExecution.start_execution()
    //├── Contract2.execute()
    //└── Contract3.execute()
    //    ├── Contract4.execute()
    //    ├── Contract5.execute()
    //    │   └── Contract7.execute()
    //    └── Contract6.execute()

contract ChainExecution {
    Contract2 private contract2;
    Contract3 private contract3;

    constructor(address _contract2, address _contract3) {
        contract2 = Contract2(_contract2);
        contract3 = Contract3(_contract3);
    }

    function start_execution() external view returns (uint256) {
        uint256 result1 = contract2.execute();
        uint256 result2 = contract3.execute();
        uint256 sum = result1 + result2;
        return sum;
    }
}

contract Contract2 {

    function execute() external pure returns (uint256) {
        return 2;
    }
}

contract Contract3 {
    Contract4 private contract4;
    Contract5 private contract5;
    Contract6 private contract6;

    constructor(address _contract4, address _contract5, address _contract6) {
        contract4 = Contract4(_contract4);
        contract5 = Contract5(_contract5);
        contract6 = Contract6(_contract6);
    }

    function execute() external view returns (uint256) {
        uint256 result1 = contract4.execute();
        uint256 result2 = contract5.execute();
        uint256 result3 = contract6.execute();
        uint256 sum = result1 + result2 + result3;
        return sum;
    }
}

contract Contract4 {

    function execute() external pure returns (uint256) {
        return 4;
    }
}

contract Contract5 {
    Contract7 private contract7;

    constructor(address _contract7) {
        contract7 = Contract7(_contract7);
    }

    function execute() external view returns (uint256) {
        uint256 result1 = contract7.execute();
        return result1 + 5;
    }
}

contract Contract6 {

    function execute() external pure returns (uint256) {
        return 6;
    }
}

contract Contract7 {

    function execute() external pure returns (uint256) {
        return 7;
    }
}


contract ChainWithRevert {
    MiddleCall public middleCall;

    constructor(address _middleCall) {
        middleCall = MiddleCall(_middleCall);
    }

    function execute_trivial_revert(address _contractCallee) public returns (bool){
        return middleCall.callContactTrivialRevert(_contractCallee);
    }

    function execute_revert_in_middle_call(address _contractCommon, address _contractCallee) public{
        middleCall.callGetTextAndDoRevert(_contractCommon, _contractCallee);
    }
}

contract ChainWithReturnData {
    MiddleCall public middleCall;

    constructor(address _middleCall) {
        middleCall = MiddleCall(_middleCall);
    }

    function start_chain_with_return_data(address payable _commonContract) public payable returns (string memory) {
        (bool success, bytes memory data) = _commonContract.call{value: msg.value}(
        abi.encodeWithSignature("getTextAndReceiveValue()")
        );

        require(success, "External call failed");
        return abi.decode(data, (string));
    }
}

contract MiddleCall {
    function callContactTrivialRevert(address _contractCallee) public returns (bool) {
        bytes memory payload = abi.encodeWithSignature("emitEventRevert()");
        (bool success, ) = _contractCallee.call(payload);
        return success;
    }

    function callGetText(address _commonContract) public view returns (string memory) {
        bytes memory payload = abi.encodeWithSignature("getText()");
        (bool success, bytes memory returnData) = _commonContract.staticcall(payload);
        require(success, "Call to getText() failed");

        return abi.decode(returnData, (string));
    }

    function callGetTextAndDoRevert(address _commonContract, address _contractCallee) public returns (bool) {
        bytes memory payload_1 = abi.encodeWithSignature("getText()");
        (bool success_1, bytes memory returnData) = _commonContract.staticcall(payload_1);
        require(success_1, "Call to getText() failed");

        bytes memory payload_2 = abi.encodeWithSignature("emitEventRevert()");
        (bool success_2, ) = _contractCallee.call(payload_2);
        return success_2;
}
}


