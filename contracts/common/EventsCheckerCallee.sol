pragma solidity >=0.8.0;


contract SubcallContract {
    address public contractAddress;

    constructor() payable {
        contractAddress = address(this);
    }

    function getValue() public pure returns (uint256) {
        return 1;
    }
}

contract EventsCheckerCallee {
    uint256 public parameter;
    address public sender;

    event EventContractCallee(string text);
    mapping(address => uint256) public addressBalances;

    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }

    function deposit() public payable {
        addressBalances[msg.sender] += msg.value;
    }

    function setParam(uint256 _param) public {
        parameter = _param;
        sender = msg.sender;
    }

    function emitEvent() public {
        emit EventContractCallee("EmitEvent");
    }

    function emitEventAssertFalse() public {
        emit EventContractCallee("EmitEvent");
        assert(false);
    }

    function emitEventRevertWithRequire() public {
        emit EventContractCallee("EmitEvent");
        require(!true, "require False");
    }

    function emitEventRevert() public {
        emit EventContractCallee("EmitEvent");
        revert("Revert Contract");
    }

    function returnNumber(uint256 number) public pure returns (uint256) {
        return number;
    }

    function notSafeDivision(uint256 number, uint256 divider) public pure returns (uint256) {
        return number / divider;
    }

    function getValue() public returns (uint256) {
        SubcallContract _subcall = SubcallContract(address(new SubcallContract()));
        return _subcall.getValue();
    }
}
