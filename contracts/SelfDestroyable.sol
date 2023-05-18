pragma solidity ^0.8.4;

contract SelfDestroyable {
    address payable public owner;
    bool public isDestroyed;
    string public text = "text";

    event FunctionCalled(string message);

    constructor() {
        owner = payable(msg.sender);
    }

    function deposit() public payable returns (bool b) {
        return true;
    }
    function destroy(address fundsRecipient) public payable{
        address payable addr = payable(fundsRecipient);
        selfdestruct(addr);
        isDestroyed = true;
    }

    function anyFunction() public {
        text = "new text";
        emit FunctionCalled("hello");
    }


    function transfer1Ether(address recipient) public returns (bool b){
        require(address(this).balance >= 1 ether, "contract balance less 1 ether");
        bool success = payable(recipient).send(1 ether);
        require(success, "transfer failed");
        return true;
    }

    receive() external payable {}
}

contract SelfDestroyableContractCaller {
    address private contractAddress;

    constructor(address _address) {
        contractAddress = _address;
    }

    function callDestroy(address fundsRecipient) public {
        (bool success, )  = address(contractAddress).call(abi.encodeWithSignature("destroy(address)", fundsRecipient));
        require(success, "callDestroy: failed call");
    }

    function callDestroyAndSendMoneyFromContract(address fundsRecipient) public {
        callDestroy(fundsRecipient);
        address(contractAddress).call(abi.encodeWithSignature("transfer1Ether(address)", fundsRecipient));
    }

    function sendMoneyFromContractAndCallDestroy(address fundsRecipient) public payable {
        address(contractAddress).call(abi.encodeWithSignature("transfer1Ether(address)", fundsRecipient));
        callDestroy(fundsRecipient);
    }
    function callDestroyTwice(address fundsRecipient) public {
        callDestroy(fundsRecipient);
        callDestroy(fundsRecipient);
    }

    function callDestroyViaDelegateCall(address fundsRecipient) public {
        (bool success, )  = address(contractAddress).delegatecall(abi.encodeWithSignature("destroy(address)", fundsRecipient));
        require(success, "callDestroy: failed call");
    }

    function callDestroyViaDelegateCallAndCreateNewContract(address fundsRecipient) public {
        (bool success, )  = address(contractAddress).delegatecall(abi.encodeWithSignature("destroy(address)", fundsRecipient));
        require(success, "callDestroy: failed call");
        contractAddress = address(new SelfDestroyable());
    }
}