pragma solidity >=0.8.0;

import "./EventsCheckerCallee.sol";

contract ChildContract {
    address public childAddr;

    constructor() payable {
        childAddr = address(this);
    }
}

contract ChildContractWithNewContractInConstructor {
    address public childAddr;
    event EventChildContractWithNewContractInConstructor(string text);

    constructor() {
        emit EventChildContractWithNewContractInConstructor("Emit Child Contract Event");
        childAddr = address(new 
        ChildContract());
    }
}

contract EventsCheckerCaller {
    uint256 public parameter;
    address public sender;

    event EventContractCaller(string text);
    event AdditionalEventContractCaller(string text);
    function deposit() public payable {}

    function setParamWithDelegateCall(
        address _contractCallee,
        uint256 _param
    ) public {
        (bool success, ) = _contractCallee.delegatecall(
            abi.encodeWithSignature("setParam(uint256)", _param)
        );
        require(success);
    }

    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }

    function depositOnContractOne(address _contractCallee) public {
        bytes memory payload = abi.encodeWithSignature("deposit()");
        (bool success, ) = _contractCallee.call{value: 1, gas: 100000}(payload);
        require(!success);
    }

    function callContactRevertWithAssertFalse(
        address _contractCallee
    ) public returns (bool) {
        emit EventContractCaller("Emit ContractCaller Event");
        bytes memory payload = abi.encodeWithSignature(
            "emitEventAssertFalse()"
        );
        (bool success, ) = _contractCallee.call(payload);
        return success;
    }

    function callContactTrivialRevert(address _contractCallee) public returns (bool) {
        emit EventContractCaller("Emit ContractCaller Event");
        bytes memory payload = abi.encodeWithSignature("emitEventRevert()");
        (bool success, ) = _contractCallee.call(payload);
        return success;
    }

    function callContactRevertInsufficientBalance(address _contractCallee) public returns (bool) {
        emit EventContractCaller("Emit ContractCaller Event");
        bytes memory payload = abi.encodeWithSignature("emitEventRevert()");
        (bool success, ) = _contractCallee.call{value: 1, gas: 100000}(payload);
        return success;
    }

    function callContractRevertWithRequire(
        address _contractCallee
    ) public returns (bool) {
        emit EventContractCaller("Emit ContractCaller Event");
        bytes memory payload = abi.encodeWithSignature(
            "emitEventRevertWithRequire()"
        );
        (bool success, ) = _contractCallee.call(payload);
        return success;
    }

    function getBalanceOfContractCallee(
        address _contractCallee
    ) public view returns (uint256) {
        EventsCheckerCallee _callee = EventsCheckerCallee(_contractCallee);
        uint256 balanceOfContractOne = _callee.getBalance();
        return balanceOfContractOne;
    }

    function emitEventAndGetBalanceOfContractCalleeWithEvents(
        address _contractCallee
    ) public returns (uint256) {
        emit EventContractCaller("Emit ContractCaller Event");
        EventsCheckerCallee _callee = EventsCheckerCallee(_contractCallee);
        _callee.emitEvent();
        uint256 balanceOfContractOne = _callee.getBalance();
        return balanceOfContractOne;
    }

    function emitEventAndGetValueContractCalleeWithEventsAndSubcall(
        address _contractCallee
    ) public returns (uint256) {
        emit EventContractCaller("Emit ContractCaller Event");
        EventsCheckerCallee _callee = EventsCheckerCallee(_contractCallee);
        _callee.emitEvent();
        uint256 balanceOfContractOne = _callee.getValue();
        return balanceOfContractOne;
    }

    function emitEventAndCallContractCalleeWithEvent(
        address _contractCallee
    ) public {
        emit EventContractCaller("Emit ContractCaller Event");
        EventsCheckerCallee _callee = EventsCheckerCallee(_contractCallee);
        _callee.emitEvent();
    }

    function emitAllEventsAndCallContractCalleeWithEvent(
        address _contractCallee
    ) public {
        emit EventContractCaller("Emit ContractCaller Event");
        emit AdditionalEventContractCaller("Emit Additional ContractCaller Event");
        EventsCheckerCallee _callee = EventsCheckerCallee(_contractCallee);
        _callee.emitEvent();
    }

    function lowLevelCallContract(
        address _contractCallee
    ) public returns (bool) {
        bytes memory payload = abi.encodeWithSignature("returnNumber(uint256)", 1);
        (bool success, ) = _contractCallee.call(payload);
        return success;
    }

    function lowLevelCallContractWithEvents(address _contractCallee) public {
        emit EventContractCaller("Emit ContractCaller Event");
        bytes memory payload = abi.encodeWithSignature("returnNumber(uint256)", 1);
        _contractCallee.call(payload);
        bytes memory payloadEvent = abi.encodeWithSignature("emitEvent()");
        _contractCallee.call(payloadEvent);
    }

    function callNotSafeDivision(
        address _contractCallee
    ) public returns (bool) {
        bytes memory payload = abi.encodeWithSignature(
            "notSafeDivision(uint256,uint256)",
            1,
            0
        );
        (bool success, ) = _contractCallee.call(payload);
        return success;
    }

    function callTypeCreate2() public returns (address) {
        bytes32 salt = bytes32(0);
        address childContract = address(new ChildContract{salt: salt}());
        return childContract;
    }

    function callChildWithEventAndContractCreationInConstructor() public returns (address) {
        address childContract = address(new ChildContractWithNewContractInConstructor());
        return childContract;
    }
}
