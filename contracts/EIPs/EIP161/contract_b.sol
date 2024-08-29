pragma solidity ^0.8.0;

contract ContractB {
    event ContractBDeployed(address indexed creator, address indexed contractAddress);
    event Result(uint256 indexed result);

    constructor() {
        emit ContractBDeployed(msg.sender, address(this));
    }

    function getOne() public returns (uint256) {
        emit Result(1);
        return 1;
    }
}
