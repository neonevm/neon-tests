pragma solidity ^0.8.0;

import "./contract_b.sol";

contract ContractA {
    event ContractBDeployed(address indexed creator, address indexed contractAddress);

    function deploy_contract() public {
        ContractB contractB = new ContractB();
        emit ContractBDeployed(msg.sender, address(contractB));
    }
}
