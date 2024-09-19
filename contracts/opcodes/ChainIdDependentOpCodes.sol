// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

contract ChainIdDependentOpCodes {

    function getChainId() public view returns (uint256) {
        uint256 id;
        assembly {
            id := chainid()
        }
        return id;
    }

    function getBalance(address _addr) public view returns (uint) {
        return _addr.balance;
    }
}

contract ChainIdDependentOpCodesCaller {

    ChainIdDependentOpCodes public chainIdDependentOpCodes;

    constructor() {
    }

    function getChainId(address _addr) public view returns (uint) {
        ChainIdDependentOpCodes my = ChainIdDependentOpCodes(_addr);
        return my.getChainId();
    }

    function getBalance(address _addr, address account) public view returns (uint) {
        ChainIdDependentOpCodes my = ChainIdDependentOpCodes(_addr);

        return my.getBalance(account);
    }
}