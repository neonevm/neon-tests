pragma solidity ^0.8.0;

import "./contract_b.sol";

contract ContractA {
    function deploy_contract() public returns(address){
        ContractB contractB = new ContractB();
        return address(contractB);
    }
}
