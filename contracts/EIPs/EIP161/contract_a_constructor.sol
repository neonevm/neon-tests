pragma solidity ^0.8.0;

import "./contract_b.sol";

contract ContractA {

    constructor() {
        ContractB contractB = new ContractB();
    }
}
